"""Ephemeral container probes with no network/host mounts or host Python execution fallback."""

import asyncio
import hashlib
import json
import uuid
from typing import Protocol

from pydantic import ConfigDict, TypeAdapter

from lumis_sdk.core.contracts import Scalar
from lumis_sdk.investigation.contracts import ProbeSpec
from lumis_sdk.investigation.process import run_bounded
from lumis_sdk.sandbox.policy import SandboxPolicy

# This trusted bootstrap is executed only inside the isolated container. No generated code runs
# in the SDK host process. The operator approves the image; runtime never pulls it implicitly.
BOOTSTRAP = """import json, pathlib, subprocess, sys
payload = json.load(sys.stdin)
root = pathlib.Path('/work')
for name, text in payload['files'].items():
    target = root / 'snapshot' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
probe = root / 'probe.py'
probe.write_text(payload['code'])
result = subprocess.run([sys.executable, '-I', str(probe)], cwd=root)
sys.exit(result.returncode)
"""


class ProbeRunner(Protocol):
    async def run(self, spec: ProbeSpec, files: dict[str, str]) -> Scalar: ...


class DockerProbeRunner:
    def __init__(self, policy: SandboxPolicy) -> None:
        if not policy.enabled or policy.image is None:
            raise ValueError("sandbox is disabled or lacks a pinned image")
        self.policy = policy

    async def run(self, spec: ProbeSpec, files: dict[str, str]) -> Scalar:
        from lumis_sdk.investigation.config import approved_file

        for name in files:
            approved_file(name)
        payload = json.dumps({"code": spec.code, "files": files}).encode()
        if len(payload) > 300000:
            raise ValueError("probe input exceeds byte budget")
        name = "lumis-probe-" + uuid.uuid4().hex
        command = [
            "docker",
            "run",
            "--name",
            name,
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "65534:65534",
            "--pids-limit",
            str(self.policy.pids),
            "--memory",
            f"{self.policy.memory_mb}m",
            "--memory-swap",
            f"{self.policy.memory_mb}m",
            "--cpus",
            str(self.policy.cpus),
            "--tmpfs",
            "/work:rw,noexec,nosuid,size=16m,mode=1777",
            "--workdir",
            "/work",
            "--entrypoint",
            "python",
            "--log-driver",
            "none",
            "-i",
            str(self.policy.image),
            "-I",
            "-c",
            BOOTSTRAP,
        ]
        try:
            result = await run_bounded(
                command,
                timeout=self.policy.timeout_seconds,
                max_bytes=self.policy.max_output_bytes,
                stdin=payload,
            )
            if result.exit_code:
                raise ValueError("probe failed or sandbox unavailable")
            raw = json.loads(result.stdout)
            if not isinstance(raw, dict) or set(raw) != {"value"}:
                raise ValueError("probe must print exactly one JSON object with scalar value")
            return TypeAdapter(Scalar, config=ConfigDict(allow_inf_nan=False)).validate_python(
                raw["value"]
            )
        finally:

            async def cleanup() -> None:
                # A cancelled CLI can leave the daemon finishing container creation. A
                # first "no such container" is not proof that the name cannot appear shortly
                # afterwards. Retry bounded cleanup; never touch another run's container.
                try:
                    async with asyncio.timeout(5):
                        for _ in range(20):
                            try:
                                result = await run_bounded(
                                    ["docker", "rm", "--force", name], timeout=1, max_bytes=1000
                                )
                                if result.exit_code == 0:
                                    return
                            except (OSError, ValueError, TimeoutError):
                                pass
                            await asyncio.sleep(0.2)
                except TimeoutError:
                    pass

            await asyncio.shield(cleanup())


def code_digest(spec: ProbeSpec) -> str:
    return hashlib.sha256(spec.code.encode()).hexdigest()
