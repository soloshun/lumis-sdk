"""Bounded subprocess I/O for fixed read-only Git and sandbox commands; never a shell port."""

import asyncio
from collections.abc import Mapping, Sequence
from typing import NamedTuple


class ProcessOutput(NamedTuple):
    exit_code: int
    stdout: bytes


async def run_bounded(
    args: Sequence[str],
    *,
    timeout: float,
    max_bytes: int,
    stdin: bytes | None = None,
    env: Mapping[str, str] | None = None,
) -> ProcessOutput:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )

    async def write() -> None:
        if stdin is not None:
            assert process.stdin is not None
            process.stdin.write(stdin)
            try:
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                process.stdin.close()

    async def read() -> bytes:
        assert process.stdout is not None
        try:
            await process.stdout.readexactly(max_bytes + 1)
        except asyncio.IncompleteReadError as error:
            return error.partial
        raise ValueError("subprocess output exceeds byte budget")

    try:
        async with asyncio.timeout(timeout):
            _, data = await asyncio.gather(write(), read())
            return ProcessOutput(await process.wait(), data)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
