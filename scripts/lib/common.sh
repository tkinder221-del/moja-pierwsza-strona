#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

load_project_config() {
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/config/brave-version.env"
  local required=(BRAVE_CORE_REPO BRAVE_CORE_REF BRAVE_VERSION CHROMIUM_VERSION PNPM_VERSION APK_TARGET_ARCH TEST_TARGET_ARCH BUILD_DIR)
  local name
  for name in "${required[@]}"; do
    [[ -n "${!name:-}" ]] || { printf 'Missing required variable: %s\n' "$name" >&2; return 1; }
  done
}

extension_gn_cli_args() {
  python3 - "${PROJECT_ROOT}/config/android-extension-args.gn" <<'PY'
from pathlib import Path
import sys

allowed = {"enable_desktop_android_extensions", "is_desktop_android"}
seen = set()
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    key, value = [part.strip() for part in line.split("=", 1)]
    if key not in allowed or value not in {"true", "false"}:
        raise SystemExit(f"Unsupported extension GN assignment: {line}")
    seen.add(key)
    print(f"{key}:{value}")
if seen != allowed:
    raise SystemExit(f"Missing extension GN assignments: {sorted(allowed - seen)}")
PY
}
