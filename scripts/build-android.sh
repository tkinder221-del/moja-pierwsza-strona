#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

PRINT_PLAN=false
[[ "${1:-}" == "--print-plan" ]] && { PRINT_PLAN=true; shift; }
[[ $# -eq 2 ]] || { echo "Usage: $0 [--print-plan] <work-root> <baseline|extensions>" >&2; exit 2; }
WORK_ROOT="$(cd "$1" && pwd)"
MODE="$2"
BRAVE_DIR="${WORK_ROOT}/src/brave"
[[ -d "$BRAVE_DIR" ]] || { echo "Missing Brave source directory: $BRAVE_DIR" >&2; exit 2; }

extra_gn=()
if [[ "$MODE" == "extensions" ]]; then
  while IFS= read -r arg; do
    extra_gn+=(--gn "$arg")
  done < <(extension_gn_cli_args)
elif [[ "$MODE" != "baseline" ]]; then
  echo "Unknown build mode: $MODE" >&2
  exit 2
fi

command=(
  pnpm run build Debug
  -C "$BUILD_DIR"
  --target_os=android
  --target_arch="$APK_TARGET_ARCH"
  --target_android_output_format=apk
  --skip_signing
  --use_remoteexec=false
  "${extra_gn[@]}"
)

printf 'cd %q\n' "$BRAVE_DIR"
printf 'JAVA_OPTS=%q ' "${JAVA_OPTS:--Xmx10G -Xms1G}"
printf '%q ' "${command[@]}"
printf '\n'

if "$PRINT_PLAN"; then
  exit 0
fi

cd "$BRAVE_DIR"
export JAVA_OPTS="${JAVA_OPTS:--Xmx10G -Xms1G}"
"${command[@]}"
