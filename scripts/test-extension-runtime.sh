#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

PRINT_PLAN=false
[[ "${1:-}" == "--print-plan" ]] && { PRINT_PLAN=true; shift; }
[[ $# -eq 1 ]] || { echo "Usage: $0 [--print-plan] <work-root>" >&2; exit 2; }
WORK_ROOT="$(cd "$1" && pwd)"
BRAVE_DIR="${WORK_ROOT}/src/brave"
[[ -d "$BRAVE_DIR" ]] || { echo "Missing Brave source directory: $BRAVE_DIR" >&2; exit 2; }

FILTER="DesktopAndroidExtensionsBrowserTest.BraveMvpFixtureContentScript:DesktopAndroidExtensionsBrowserTest.ServiceWorkerBasedExtension:DesktopAndroidExtensionsBrowserTest.ContentScriptInjection:DesktopAndroidExtensionsBrowserTest.StorageApiTestStorageAreaLocal:DesktopAndroidExtensionsBrowserTest.MessagePassing"
extra_gn=()
while IFS= read -r arg; do
  extra_gn+=(--gn "$arg")
done < <(extension_gn_cli_args)

command=(
  pnpm run test browser_tests
  --target_os=android
  --target_arch="$TEST_TARGET_ARCH"
  --manual_android_test_device
  "${extra_gn[@]}"
  --filter="$FILTER"
)

printf 'bash %q %q\n' "${SCRIPT_DIR}/stage-test-fixture.sh" "${WORK_ROOT}/src"
printf 'cd %q\n' "$BRAVE_DIR"
printf '%q ' "${command[@]}"
printf '\n'

if "$PRINT_PLAN"; then
  exit 0
fi

bash "${SCRIPT_DIR}/stage-test-fixture.sh" "${WORK_ROOT}/src"
cd "$BRAVE_DIR"
"${command[@]}"
