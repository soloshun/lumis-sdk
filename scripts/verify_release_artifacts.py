"""Fail closed when Python release archives contain unsafe or unexpected files."""

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

FORBIDDEN_SUFFIXES = {".env", ".key", ".pem", ".p12", ".pfx"}
FORBIDDEN_PARTS = {".git", ".pytest_cache", "__pycache__"}


def main() -> None:
    """Verify exactly one wheel and source archive in a release directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("dist_dir", type=Path)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    wheels = sorted(args.dist_dir.glob("*.whl"))
    source_archives = sorted(args.dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(source_archives) != 1:
        raise SystemExit("expected exactly one wheel and one .tar.gz source archive")
    normalized_name = args.distribution.replace("-", "_")
    expected_prefix = f"{normalized_name}_{args.version}"
    for archive in [*wheels, *source_archives]:
        if not archive.name.replace("-", "_").startswith(expected_prefix):
            raise SystemExit(f"unexpected artifact name: {archive.name}")

    wheel_names = _wheel_members(wheels[0])
    source_names = _source_members(source_archives[0])
    _verify_names(wheel_names, wheels[0])
    _verify_names(source_names, source_archives[0])
    _require_suffix(wheel_names, ".dist-info/METADATA", wheels[0])
    _require_contains(source_names, "/pyproject.toml", source_archives[0])
    _require_contains(source_names, "/README.md", source_archives[0])

    print(f"Verified release contents: {wheels[0].name}, {source_archives[0].name}")


def _wheel_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def _source_members(path: Path) -> list[str]:
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                raise SystemExit(f"release archive contains a link: {member.name}")
        return archive.getnames()


def _verify_names(names: list[str], archive: Path) -> None:
    if not names:
        raise SystemExit(f"empty release archive: {archive}")
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"unsafe archive path in {archive}: {name}")
        lowered_parts = {part.lower() for part in path.parts}
        if lowered_parts & FORBIDDEN_PARTS:
            raise SystemExit(f"development-only path in {archive}: {name}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise SystemExit(f"secret-bearing file type in {archive}: {name}")


def _require_suffix(names: list[str], suffix: str, archive: Path) -> None:
    if not any(name.endswith(suffix) for name in names):
        raise SystemExit(f"{archive} is missing required {suffix}")


def _require_contains(names: list[str], fragment: str, archive: Path) -> None:
    if not any(fragment in name for name in names):
        raise SystemExit(f"{archive} is missing required {fragment}")


if __name__ == "__main__":
    main()
