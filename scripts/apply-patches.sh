#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PATCH_DIR="${OVERLAY_PATCH_DIR:-${PROJECT_ROOT}/patches}"
[[ $# -eq 1 ]] || { echo "Usage: $0 <chromium-src-root>" >&2; exit 2; }
SRC_ROOT="$(cd "$1" && pwd)"
mapfile -t patches < <(find "$PATCH_DIR" -maxdepth 1 -type f -name '[0-9][0-9][0-9][0-9]-*.patch' -print | sort)
[[ ${#patches[@]} -gt 0 ]] || { echo "No overlay patches to apply."; exit 0; }
for patch_file in "${patches[@]}"; do
  echo "Applying $(basename "$patch_file")"
  patch --batch --forward --dry-run -p1 -d "$SRC_ROOT" < "$patch_file" >/dev/null
  patch --batch --forward -p1 -d "$SRC_ROOT" < "$patch_file"
done
