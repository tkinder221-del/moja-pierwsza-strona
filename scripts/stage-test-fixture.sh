#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
[[ $# -eq 1 ]] || { echo "Usage: $0 <chromium-src-root>" >&2; exit 2; }
SRC_ROOT="$(cd "$1" && pwd)"
SOURCE="${PROJECT_ROOT}/fixtures/test-extension"
DEST="${SRC_ROOT}/chrome/test/data/extensions/brave_android_mvp"
[[ -d "$SOURCE" ]] || { echo "Fixture source missing: $SOURCE" >&2; exit 1; }
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "${SOURCE}/." "$DEST/"
