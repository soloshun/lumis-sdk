"""Two-process synthetic demonstration of explicit shared operational memory."""

import argparse
import asyncio
import time
from pathlib import Path

from lumis_postgres_memory import PostgresMemoryPlugin

from lumis_sdk.config import PostgresMemoryConfig, load_config
from lumis_sdk.ports import MemoryQuery, MemoryStore
from lumis_sdk.testkit import make_test_episode, make_test_resolution


async def write_episode(store: MemoryStore) -> None:
    await store.save_incident(make_test_episode())
    await store.record_resolution(make_test_resolution())
    print("writer: saved human-confirmed episode")


async def read_episode(store: MemoryStore) -> None:
    matches = await store.search(MemoryQuery(text="fixture pipeline recovered"))
    if not matches or matches[0].episode.resolution is None:
        raise SystemExit("reader: confirmed shared memory was not found")
    match = matches[0]
    print(
        f"reader: incident={match.episode.incident_id} "
        f"truth={match.episode.truth_state.value} reasons={'; '.join(match.reasons)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["write", "write-hold", "read"])
    args = parser.parse_args()
    config = load_config(Path(__file__).with_name("lumis.yml"))
    if not isinstance(config.memory, PostgresMemoryConfig):
        raise SystemExit("cookbook requires provider: postgres")
    store = PostgresMemoryPlugin().create(config.memory)
    if args.operation in {"write", "write-hold"}:
        asyncio.run(write_episode(store))
        if args.operation == "write-hold":
            Path("/tmp/lumis-writer-ready").touch()
            time.sleep(300)
    else:
        asyncio.run(read_episode(store))


if __name__ == "__main__":
    main()
