#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

[[ $# -eq 1 ]] || { echo "Usage: $0 <work-root>" >&2; exit 2; }
WORK_ROOT="$(cd "$1" && pwd)"
GN="${WORK_ROOT}/src/buildtools/linux64/gn"
OUT="${WORK_ROOT}/src/out/${BUILD_DIR}"
[[ -x "$GN" ]] || { echo "GN binary not found or not executable: $GN" >&2; exit 1; }
[[ -d "$OUT" ]] || { echo "GN output directory not found: $OUT" >&2; exit 1; }

check_arg() {
  local name="$1"
  local expected="$2"
  local output
  output="$("$GN" args "$OUT" --list="$name")"
  printf '%s\n' "$output"
  if ! grep -Eq "Current value = ${expected}([[:space:]]|$)" <<<"$output"; then
    printf 'Unexpected GN value for %s; expected %s\n' "$name" "$expected" >&2
    return 1
  fi
}

check_arg enable_desktop_android_extensions true
check_arg enable_extensions_core true
check_arg is_desktop_android false
