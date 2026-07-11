#!/usr/bin/env bash
# Verify one published OpenARIA release in an isolated temporary environment.

set -euo pipefail

PACKAGE_NAME="${1:-openaria}"
PACKAGE_VERSION="${2:-0.0.1}"
INDEX_URL="${3:-https://pypi.org/simple/}"
EXTRA_INDEX_URL="${4:-https://pypi.org/simple/}"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/openaria-publish-check.XXXXXX")"
VENV_DIR="$WORK_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
CLI="$VENV_DIR/bin/openaria"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "OpenARIA published-package verification"
echo "  package: $PACKAGE_NAME==$PACKAGE_VERSION"
echo "  index:   $INDEX_URL"
echo "  work:    $WORK_DIR"

uv venv "$VENV_DIR" --python 3.11 >/dev/null
uv pip install \
  --python "$PYTHON" \
  --index-url "$INDEX_URL" \
  --extra-index-url "$EXTRA_INDEX_URL" \
  "$PACKAGE_NAME==$PACKAGE_VERSION" >/dev/null

INSTALLED_VERSION="$($PYTHON -c 'import openaria; print(openaria.__version__)')"
if [[ "$INSTALLED_VERSION" != "$PACKAGE_VERSION" ]]; then
  echo "Verification failed: imported version $INSTALLED_VERSION, expected $PACKAGE_VERSION." >&2
  exit 1
fi

CLI_VERSION="$($CLI --version)"
if [[ "$CLI_VERSION" != "$PACKAGE_VERSION" ]]; then
  echo "Verification failed: CLI version $CLI_VERSION, expected $PACKAGE_VERSION." >&2
  exit 1
fi

"$CLI" init --destination "$WORK_DIR/project" >/dev/null
printf 'ERROR OPENARIA_RELEASE_CHECK\n' > "$WORK_DIR/project/failure.log"
"$CLI" doctor --config "$WORK_DIR/project/openaria.yml" >/dev/null
"$CLI" rules validate --config "$WORK_DIR/project/openaria.yml" --json >/dev/null

echo "Verification passed"
echo "  imported package version: $INSTALLED_VERSION"
echo "  CLI version:              $CLI_VERSION"
echo "  CLI initialization:       passed"
echo "  configuration doctor:     passed"
echo "  rule validation:          passed"
echo "  cleanup:                  removing $WORK_DIR"
