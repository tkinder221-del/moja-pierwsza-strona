#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

[[ $# -eq 2 ]] || { echo "Usage: $0 <work-root> <artifact-dir>" >&2; exit 2; }
WORK_ROOT="$(cd "$1" && pwd)"
ARTIFACT_DIR="$2"
OUT_DIR="${WORK_ROOT}/src/out/${BUILD_DIR}"
[[ -d "$OUT_DIR" ]] || { echo "Build output directory not found: $OUT_DIR" >&2; exit 1; }

mapfile -t apks < <(find "$OUT_DIR" -type f -name '*.apk' -print | sort)
[[ ${#apks[@]} -gt 0 ]] || { echo "No APK artifacts found below $OUT_DIR" >&2; exit 1; }

rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR/apk"
for apk in "${apks[@]}"; do
  cp "$apk" "$ARTIFACT_DIR/apk/$(basename "$apk")"
done

overlay_commit="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || printf 'unknown')"
cat > "$ARTIFACT_DIR/build-metadata.txt" <<META
BRAVE_CORE_REF=${BRAVE_CORE_REF}
BRAVE_VERSION=${BRAVE_VERSION}
CHROMIUM_VERSION=${CHROMIUM_VERSION}
APK_TARGET_ARCH=${APK_TARGET_ARCH}
BUILD_DIR=${BUILD_DIR}
OVERLAY_COMMIT=${overlay_commit}
META
