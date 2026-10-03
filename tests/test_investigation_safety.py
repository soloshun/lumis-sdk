"""Allowlisted code, fixed subprocesses and opt-in real container qualification."""

import asyncio
import os
import subprocess
import sys

import pytest

from lumis_sdk.connectors.code import CodeSnapshot, read_scoped_file
from lumis_sdk.investigation.config import CodeRepository
from lumis_sdk.investigation.contracts import ProbeSpec
from lumis_sdk.investigation.process import ProcessOutput, run_bounded
from lumis_sdk.investigation.providers import configured_investigator
from lumis_sdk.runtime.project import ModelSettings
from lumis_sdk.sandbox.policy import SandboxPolicy
from lumis_sdk.sandbox.runner import DockerProbeRunner


@pytest.mark.parametrize(
    "path",
    [
        "../x.py",
        "/x.py",
        ".env",
        ".git/config",
        "a/../x.py",
        "a//x.py",
        "a/.secrets.py",
        "x.bin",
        "-option.py",
    ],
)
def test_repository_allowlist_rejects_unsafe_paths(tmp_path, path):
    with pytest.raises(ValueError):
        CodeRepository(id="repo", root=str(tmp_path), entity_ids=("service",), files=(path,))


def test_code_snapshot_never_imports_and_rejects_symlinks_binary_large_fifo(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("raise RuntimeError('must never import')\n")
    snapshot = CodeSnapshot(
        CodeRepository(
            id="repo", root=str(tmp_path), entity_ids=("service",), files=("source.py",)
        ),
        tmp_path,
    )
    source.write_text("changed")
    assert "must never import" in snapshot.read("source.py")
    assert "source.py:1:" in snapshot.search("RuntimeError")
    assert snapshot.search(".*") == ""
    with pytest.raises(ValueError):
        snapshot.read("not-approved.py")
    (tmp_path / "link.py").symlink_to(source)
    with pytest.raises(OSError):
        read_scoped_file(tmp_path, "link.py")
    (tmp_path / "directory").symlink_to(tmp_path)
    with pytest.raises(OSError):
        read_scoped_file(tmp_path, "directory/source.py")
    (tmp_path / "binary.py").write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        read_scoped_file(tmp_path, "binary.py")
    (tmp_path / "large.py").write_bytes(b"x" * 64001)
    with pytest.raises(ValueError, match="byte"):
        read_scoped_file(tmp_path, "large.py")
    os.mkfifo(tmp_path / "fifo.py")
    with pytest.raises(ValueError, match="regular"):
        read_scoped_file(tmp_path, "fifo.py")


def test_git_reads_only_approved_paths_without_external_diff(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init")
    git("config", "user.email", "test@example.test")
    git("config", "user.name", "Test")
    for name in ("allowed.py", "hidden.py"):
        (tmp_path / name).write_text("value = 1\n")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-m", "baseline")
    before = git("rev-parse", "HEAD")
    for name in ("allowed.py", "hidden.py"):
        (tmp_path / name).write_text("value = 2\n")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-m", "change")
    after = git("rev-parse", "HEAD")
    git("config", "diff.external", "false")
    snapshot = CodeSnapshot(
        CodeRepository(id="r", root=str(tmp_path), entity_ids=("service",), files=("allowed.py",)),
        tmp_path,
    )
    output = asyncio.run(
        snapshot.git(
            "git.diff",
            since="2000-01-01",
            until="2100-01-01",
            base_commit=before,
            head_commit=after,
        )
    )
    assert "+value = 2" in output and "hidden.py" not in output
    assert git("status", "--porcelain") == ""
    log = asyncio.run(
        snapshot.git(
            "git.log", since="2000-01-01T00:00:00+00:00", until="2030-01-01T00:00:00+00:00"
        )
    )
    assert after in log and before in log
    assert "change" not in log  # subjects are opt-in
    (tmp_path / "allowed.py").write_text("value = 3\n")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-m", "Raise pool size password=hunter2secret")
    with_subjects = CodeSnapshot(
        CodeRepository(
            id="r",
            root=str(tmp_path),
            entity_ids=("service",),
            files=("allowed.py",),
            include_commit_subjects=True,
        ),
        tmp_path,
    )
    log = asyncio.run(
        with_subjects.git(
            "git.log", since="2000-01-01T00:00:00+00:00", until="2030-01-01T00:00:00+00:00"
        )
    )
    assert f"{after} " in log and " change" in log and "Raise pool size" in log
    assert "hunter2secret" not in log
    with pytest.raises(ValueError, match="full commit"):
        asyncio.run(
            snapshot.git("git.diff", since="", until="", base_commit="HEAD", head_commit=after)
        )


def test_bounded_process_timeout_output_and_cancel_reap_children(monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []

    async def track(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", track)

    async def run():
        result = await run_bounded([sys.executable, "-c", "print('ok')"], timeout=2, max_bytes=100)
        assert result.stdout == b"ok\n"
        with pytest.raises(ValueError, match="byte"):
            await run_bounded([sys.executable, "-c", "print('x'*10000)"], timeout=2, max_bytes=100)
        with pytest.raises(TimeoutError):
            await run_bounded(
                [sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.02, max_bytes=100
            )
        task = asyncio.create_task(
            run_bounded(
                [sys.executable, "-c", "import time; time.sleep(5)"], timeout=10, max_bytes=100
            )
        )
        await asyncio.sleep(0.03)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert all(process.returncode is not None for process in processes)

    asyncio.run(run())


@pytest.mark.parametrize("provider", ["openrouter", "openai", "anthropic", "gemini"])
def test_native_provider_factory_is_offline_and_requires_explicit_key(monkeypatch, provider):
    settings = ModelSettings(
        provider=provider,
        model="openai/test-model" if provider == "openrouter" else "test-model",
        api_key_env="LUMIS_TEST_KEY",
    )
    monkeypatch.delenv("LUMIS_TEST_KEY", raising=False)

    async def absent():
        async with configured_investigator(settings, timeout=1):
            pytest.fail("must not silently use another credential")

    with pytest.raises(ValueError, match="credential"):
        asyncio.run(absent())
    monkeypatch.setenv("LUMIS_TEST_KEY", "test-not-a-secret")

    async def configured():
        async with configured_investigator(settings, timeout=1) as agent:
            assert hasattr(agent, "agent")

    asyncio.run(configured())


def test_sandbox_requires_explicit_pinned_image():
    with pytest.raises(ValueError):
        DockerProbeRunner(SandboxPolicy())
    for image in (None, "python:3.12", "--privileged", "python@sha256:abc"):
        with pytest.raises(ValueError):
            SandboxPolicy(enabled=True, image=image)


def test_sandbox_cleanup_retries_daemon_creation_race(monkeypatch):
    calls = []

    async def fake_run(args, **kwargs):
        calls.append(args)
        if args[1] == "run":
            raise TimeoutError
        return ProcessOutput(1 if len(calls) == 2 else 0, b"")

    monkeypatch.setattr("lumis_sdk.sandbox.runner.run_bounded", fake_run)
    runner = DockerProbeRunner(SandboxPolicy(enabled=True, image="python@sha256:" + "a" * 64))
    with pytest.raises(TimeoutError):
        asyncio.run(
            runner.run(
                ProbeSpec(hypothesis_id="h", query_id="q", purpose="Race check", code="print(1)"),
                {},
            )
        )
    assert len(calls) == 3
    assert calls[1] == calls[2] and calls[1][:3] == ["docker", "rm", "--force"]


IMAGE = os.environ.get("LUMIS_TEST_SANDBOX_IMAGE")


@pytest.mark.skipif(not IMAGE, reason="explicit digest-pinned Docker qualification image required")
def test_docker_real_isolation_and_snapshot_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMIS_HOST_ONLY_TEST", "must-not-forward")
    source = tmp_path / "source.py"
    source.write_text("value = 1\n")
    code = """
import json, os, pathlib, socket
assert os.getuid() == 65534
assert 'LUMIS_HOST_ONLY_TEST' not in os.environ
assert pathlib.Path('snapshot/source.py').read_text() == 'value = 1\\n'
pathlib.Path('snapshot/source.py').write_text('sandbox-only')
try:
    pathlib.Path('/etc/lumis-write-test').write_text('bad')
except OSError:
    pass
else:
    raise AssertionError('root filesystem writable')
s = socket.socket()
s.settimeout(0.5)
try:
    s.connect(('192.0.2.1', 80))
except OSError:
    pass
else:
    raise AssertionError('network escape')
finally:
    s.close()
print(json.dumps({'value': True}))
"""
    runner = DockerProbeRunner(SandboxPolicy(enabled=True, image=IMAGE))
    value = asyncio.run(
        runner.run(
            ProbeSpec(hypothesis_id="h", query_id="q", purpose="Isolation conformance", code=code),
            {"source.py": source.read_text()},
        )
    )
    assert value is True and source.read_text() == "value = 1\n"


@pytest.mark.skipif(not IMAGE, reason="explicit digest-pinned Docker qualification image required")
@pytest.mark.parametrize(
    "code,timeout",
    [
        ("import time; time.sleep(60)", 1),
        ("print('x' * 100000)", 10),
        ("print('not JSON')", 10),
        ("print('{\"value\": NaN}')", 10),
    ],
)
def test_docker_failure_cleanup_and_no_host_fallback(code, timeout):
    policy = SandboxPolicy(enabled=True, image=IMAGE, timeout_seconds=timeout, max_output_bytes=100)
    with pytest.raises((ValueError, TimeoutError)):
        asyncio.run(
            DockerProbeRunner(policy).run(
                ProbeSpec(hypothesis_id="h", query_id="q", purpose="Failure boundary", code=code),
                {},
            )
        )
    result = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "name=lumis-probe-"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert not result.stdout.strip()


@pytest.mark.skipif(not IMAGE, reason="explicit digest-pinned Docker qualification image required")
def test_docker_cancellation_cleans_container():
    async def run():
        runner = DockerProbeRunner(SandboxPolicy(enabled=True, image=IMAGE))
        task = asyncio.create_task(
            runner.run(
                ProbeSpec(
                    hypothesis_id="h",
                    query_id="q",
                    purpose="Cancellation",
                    code="import time; time.sleep(60)",
                ),
                {},
            )
        )
        await asyncio.sleep(1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    result = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "name=lumis-probe-"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert not result.stdout.strip()
