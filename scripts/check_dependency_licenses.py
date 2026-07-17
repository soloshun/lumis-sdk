"""Reject dependency licenses that conflict with the repository's distribution policy."""

import argparse
import json
import re
from pathlib import Path

DENIED_IDENTIFIERS = {"AGPL-3.0", "GPL-3.0", "SSPL-1.0"}


def main() -> None:
    """Inspect pip-licenses JSON and fail when a denied identifier is present."""
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.report.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("license report must be a JSON array")
    denied = denied_licenses(payload)
    if denied:
        raise SystemExit("Denied dependency licenses:\n" + "\n".join(denied))
    print(f"Reviewed {len(payload)} dependency license records: no denied license found")


def denied_licenses(payload: list[object]) -> list[str]:
    """Return package/license rows matching an exact denied SPDX family."""
    denied: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            raise SystemExit("license report entries must be objects")
        name = str(item.get("Name", "unknown"))
        license_text = str(item.get("License", "UNKNOWN"))
        tokens = re.findall(r"[A-Za-z0-9.-]+", license_text)
        matches = sorted(
            identifier
            for identifier in DENIED_IDENTIFIERS
            if any(token.startswith(identifier) for token in tokens)
        )
        if matches:
            denied.append(f"{name}: {license_text}")
    return denied


if __name__ == "__main__":
    main()
