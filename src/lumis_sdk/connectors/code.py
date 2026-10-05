"""Explicit, no-symlink text snapshots and fixed read-only Git inspection."""

import hashlib
import json
import os
from pathlib import Path

from lumis_sdk.investigation.config import CodeRepository, approved_file
from lumis_sdk.investigation.process import run_bounded
from lumis_sdk.security.redaction import redact_text

MAX_FILE_BYTES = 64000
MAX_SNAPSHOT_BYTES = 256000


def read_scoped_file(root: Path, path: str) -> str:
    """Traverse through directory descriptors: symlink races cannot redirect the read."""
    parts = Path(approved_file(path)).parts
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = next_descriptor
        file_descriptor = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor
        )
        import stat

        try:
            if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
                raise ValueError("code snapshot requires regular files")
            with os.fdopen(file_descriptor, "rb", closefd=False) as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ValueError("code file exceeds byte budget")
            return redact_text(data.decode("utf-8"))
        finally:
            os.close(file_descriptor)
    finally:
        os.close(descriptor)


class CodeSnapshot:
    """Read once, then inspect immutable approved text; never import the consumer's modules."""

    def __init__(self, repository: CodeRepository, base: Path) -> None:
        raw = Path(repository.root)
        self.root = raw if raw.is_absolute() else base / raw
        # The declared root itself must not be a link. Parent paths are operator-controlled.
        self.repository = repository
        self.files = {path: read_scoped_file(self.root, path) for path in repository.files}
        self.serialized = json.dumps(self.files, sort_keys=True)
        if len(self.serialized.encode()) > MAX_SNAPSHOT_BYTES:
            raise ValueError("repository snapshot exceeds byte budget")
        self.digest = hashlib.sha256(self.serialized.encode()).hexdigest()

    def read(self, path: str) -> str:
        if path not in self.files:
            raise ValueError("file is not allowlisted")
        return self.files[path]

    def search(self, text: str) -> str:
        """Literal search only: no regular expressions or unbounded repository traversal."""
        matches = [
            f"{path}:{line}: {content}"
            for path, body in self.files.items()
            for line, content in enumerate(body.splitlines(), 1)
            if text in content
        ]
        return "\n".join(matches)

    async def git(
        self,
        operation: str,
        *,
        since: str,
        until: str,
        base_commit: str | None = None,
        head_commit: str | None = None,
    ) -> str:
        command = [
            "git",
            "--no-pager",
            "--no-optional-locks",
            "-C",
            str(self.root),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
        ]
        if operation == "git.log":
            command += [
                "log",
                "--max-count=20",
                "--format=%H %cI %s"
                if self.repository.include_commit_subjects
                else "--format=%H %cI",
                f"--since={since}",
                f"--until={until}",
            ]
        elif operation == "git.diff" and base_commit and head_commit:
            import re

            if not all(
                re.fullmatch(r"[a-f0-9]{40}", commit) for commit in (base_commit, head_commit)
            ):
                raise ValueError("Git diff requires full commit SHAs")
            command += ["diff", "--no-ext-diff", "--no-textconv", base_commit, head_commit]
        else:
            raise ValueError("unsupported Git operation")
        command += ["--", *self.repository.files]
        result = await run_bounded(
            command,
            timeout=5,
            max_bytes=MAX_FILE_BYTES,
            env={
                "PATH": os.defpath,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
        if result.exit_code:
            raise ValueError("Git inspection unavailable")
        text = result.stdout.decode("utf-8")
        if operation == "git.log":
            # Structural commit IDs/timestamps are validated, not redacted: free-text card
            # redaction could corrupt a SHA and make a subsequent approved diff unusable. Optional
            # subjects (one line each, operator opt-in) are untrusted text: redacted and truncated.
            import re

            structural = r"[a-f0-9]{40} \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})"
            lines = []
            for line in text.splitlines():
                match = re.fullmatch(f"({structural})(?: (.*))?", line)
                if match is None or (
                    match.group(2) is not None and not self.repository.include_commit_subjects
                ):
                    raise ValueError("unexpected Git metadata format")
                prefix, subject = match.groups()
                lines.append(
                    prefix if subject is None else f"{prefix} {redact_text(subject)[:200]}"
                )
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
        return redact_text(text)
