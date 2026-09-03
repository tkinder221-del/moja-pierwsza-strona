#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

PRINT_PLAN=false
[[ "${1:-}" == "--print-plan" ]] && { PRINT_PLAN=true; shift; }
[[ $# -eq 1 ]] || { echo "Usage: $0 [--print-plan] <work-root>" >&2; exit 2; }
WORK_ROOT="$(mkdir -p "$1" && cd "$1" && pwd)"
BRAVE_DIR="${WORK_ROOT}/src/brave"

if "$PRINT_PLAN"; then
  cat <<PLAN
clone ${BRAVE_CORE_REPO} into ${BRAVE_DIR}
checkout ${BRAVE_CORE_REF}
expected Brave version: ${BRAVE_VERSION}
expected Chromium version: ${CHROMIUM_VERSION}
corepack disable
npm install --global pnpm@${PNPM_VERSION}
pnpm run init --target_os=android --target_arch=${APK_TARGET_ARCH}
${WORK_ROOT}/src/build/install-build-deps.sh --android
PLAN
  exit 0
fi

mkdir -p "${WORK_ROOT}/src"
[[ -d "${BRAVE_DIR}/.git" ]] || git clone "${BRAVE_CORE_REPO}" "${BRAVE_DIR}"
git -C "${BRAVE_DIR}" fetch origin
git -C "${BRAVE_DIR}" checkout --detach "${BRAVE_CORE_REF}"

python3 - "${BRAVE_DIR}/package.json" "${BRAVE_VERSION}" "${CHROMIUM_VERSION}" <<'PY'
import json
from pathlib import Path
import sys
package = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if package["version"] != sys.argv[2]:
    raise SystemExit(f"Brave version mismatch: {package['version']} != {sys.argv[2]}")
actual_chromium = package["config"]["projects"]["chrome"]["tag"]
if actual_chromium != sys.argv[3]:
    raise SystemExit(f"Chromium version mismatch: {actual_chromium} != {sys.argv[3]}")
PY

# Corepack currently rejects Brave Core's devEngines package-manager range
# (`pnpm@>=11.11.0`) as a non-exact package-manager specification. Use the
# minimum supported pnpm release directly so the repository's own engine
# constraint remains satisfied without the Corepack project-spec shim.
corepack disable || true
npm install --global "pnpm@${PNPM_VERSION}"
pnpm --version

cd "${BRAVE_DIR}"
pnpm run init --target_os=android --target_arch="${APK_TARGET_ARCH}"
"${WORK_ROOT}/src/build/install-build-deps.sh" --android
