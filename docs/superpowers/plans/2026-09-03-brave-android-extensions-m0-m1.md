# Brave Android Extensions M0-M1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible Brave-derived Android debug APK with Chromium's upstream Android extension core enabled and prove that a deterministic Manifest V3 fixture extension executes on Android.

**Architecture:** Keep this repository as a small overlay/build orchestrator. Pin Brave Core, let Brave fetch its matching Chromium, apply deterministic root-relative patches, pass extension GN arguments while keeping the normal mobile Android form factor, build an ARM64 APK, and run focused Chromium `browser_tests` on an Android x86 emulator.

**Tech Stack:** Bash, Python 3 standard-library `unittest`, GitHub Actions, Brave Core 1.96.43, Chromium 153.0.8010.18, Node 24.16+, pnpm 11.11+, GN/Ninja/Siso through Brave tooling, Chromium extensions framework, Android browser tests.

**Spec:** `docs/superpowers/specs/2026-09-03-brave-android-extensions-design.md`

## Global Constraints

- Pin Brave Core to `f437ba81810858a15a961f13aab4fa24bb3ccce2` (`1.96.43`) and verify its Chromium tag is `153.0.8010.18` before initialization.
- Respect the pinned Brave Core engine constraints: Node `>=24.16.0 <25.0.0`, pnpm `>=11.11.0`.
- Keep `is_desktop_android=false` so the product remains the regular mobile Brave UI.
- Enable the upstream extension path with `enable_desktop_android_extensions=true`; verify the derived `enable_extensions_core=true` after GN generation.
- `config/android-extension-args.gn` is the single source of truth for extension GN command-line args. Scripts parse it rather than duplicating the values.
- Do not revive Brave's historical Android-extension proof of concept or broadly remove `IS_ANDROID`/`is_android` guards.
- No production Chromium patch is permitted until an actual M1 compile/runtime failure proves one is required. The first planned patch is test-only.
- M0-M1 cover build reproducibility and extension runtime. Mobile manager, arbitrary CRX install, extension popup UX, Chrome Web Store, release signing, and public distribution are M2+.
- APK target: `arm64`. Runtime test target: `x86` Android emulator.
- Debug/development artifacts are unofficial and unsigned for release purposes.
- Never commit signing keys or secrets.
- GitHub-hosted runners are best-effort. The build workflow also supports `self-hosted` because Chromium may exceed hosted disk/RAM/time limits.
- Initial workflows use only GitHub-maintained actions: `actions/checkout@v4`, `actions/setup-node@v4`, `actions/upload-artifact@v4`.
- Every shell script uses `set -euo pipefail`; command-producing scripts have a non-destructive `--print-plan` mode.
- M2-M5 receive separate plans only after the M1 completion gate is green.

## Verified upstream facts used by this plan

At the pinned Brave Core revision:

- Brave Core version is `1.96.43` and its Chromium tag is `153.0.8010.18`.
- Brave Android builds are driven by `pnpm run init/build --target_os=android`.
- `build/commands/lib/buildOptions.ts` supports `--target_android_output_format` and repeatable `--gn key:value` arguments.
- Chromium 153 contains `chrome/browser/extensions/desktop_android_extensions_browsertest.cc` (no `desktop_android/` directory in this path).
- That test already contains `ServiceWorkerBasedExtension`, `ContentScriptInjection`, `StorageApiTestStorageAreaLocal`, and `MessagePassing`.
- Brave's documented suite name for Chromium browser tests is `browser_tests`; `brave_browser_tests` is for tests in Brave source.

## File map

```text
README.md
config/brave-version.env
config/android-extension-args.gn
patches/README.md
patches/0001-brave-android-extension-fixture-test.patch
fixtures/test-extension/manifest.json
fixtures/test-extension/background.js
fixtures/test-extension/content_script.js
fixtures/test-extension/popup.html
fixtures/test-extension/popup.js
scripts/lib/common.sh
scripts/bootstrap.sh
scripts/apply-patches.sh
scripts/verify-patches.sh
scripts/stage-test-fixture.sh
scripts/build-android.sh
scripts/collect-artifacts.sh
scripts/verify-extension-build.sh
scripts/test-extension-runtime.sh
tests/__init__.py
tests/test_config.py
tests/test_bootstrap.py
tests/test_patch_scripts.py
tests/test_build_plan.py
tests/test_fixture.py
tests/test_runtime_test_plan.py
tests/test_workflows.py
.github/workflows/verify.yml
.github/workflows/build-android-apk.yml
.github/workflows/runtime-extension-tests.yml
docs/compatibility.md
docs/self-hosted-runner.md
```

---

### Task 1: Lock the upstream and extension-build contract

**Files:**
- Create: `config/brave-version.env`
- Create: `config/android-extension-args.gn`
- Create: `scripts/lib/common.sh`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Modify: `README.md`

**Interfaces:**
- `load_project_config()` exports the pinned versions/build values.
- `extension_gn_cli_args()` prints one Brave-compatible `key:value` argument per line from `config/android-extension-args.gn`.

- [ ] **Step 1: Write failing config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


class ProjectConfigTest(unittest.TestCase):
    def test_upstream_pin(self) -> None:
        values = parse_env(ROOT / "config" / "brave-version.env")
        self.assertEqual(values["BRAVE_CORE_REPO"], "https://github.com/brave/brave-core.git")
        self.assertEqual(values["BRAVE_CORE_REF"], "f437ba81810858a15a961f13aab4fa24bb3ccce2")
        self.assertEqual(values["BRAVE_VERSION"], "1.96.43")
        self.assertEqual(values["CHROMIUM_VERSION"], "153.0.8010.18")
        self.assertEqual(values["APK_TARGET_ARCH"], "arm64")
        self.assertEqual(values["TEST_TARGET_ARCH"], "x86")
        self.assertEqual(values["BUILD_DIR"], "BraveExtDebug")

    def test_extension_gn_file(self) -> None:
        text = (ROOT / "config" / "android-extension-args.gn").read_text(encoding="utf-8")
        self.assertEqual(
            [line.strip() for line in text.splitlines() if line.strip()],
            [
                "enable_desktop_android_extensions = true",
                "is_desktop_android = false",
            ],
        )

    def test_extension_gn_cli_conversion(self) -> None:
        script = f'''source "{ROOT}/scripts/lib/common.sh"; extension_gn_cli_args'''
        result = subprocess.run(["bash", "-c", script], text=True, capture_output=True, check=True)
        self.assertEqual(
            result.stdout.splitlines(),
            ["enable_desktop_android_extensions:true", "is_desktop_android:false"],
        )


if __name__ == "__main__":
    unittest.main()
```

Create empty `tests/__init__.py`.

- [ ] **Step 2: Run and confirm RED**

```bash
python3 -m unittest tests.test_config -v
```

Expected: missing config/common script failures.

- [ ] **Step 3: Add the pin and GN source-of-truth files**

`config/brave-version.env`:

```dotenv
BRAVE_CORE_REPO=https://github.com/brave/brave-core.git
BRAVE_CORE_REF=f437ba81810858a15a961f13aab4fa24bb3ccce2
BRAVE_VERSION=1.96.43
CHROMIUM_VERSION=153.0.8010.18
APK_TARGET_ARCH=arm64
TEST_TARGET_ARCH=x86
BUILD_DIR=BraveExtDebug
```

`config/android-extension-args.gn`:

```gn
enable_desktop_android_extensions = true
is_desktop_android = false
```

- [ ] **Step 4: Implement shared config helpers**

`scripts/lib/common.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

load_project_config() {
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/config/brave-version.env"
  local required=(BRAVE_CORE_REPO BRAVE_CORE_REF BRAVE_VERSION CHROMIUM_VERSION APK_TARGET_ARCH TEST_TARGET_ARCH BUILD_DIR)
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
```

- [ ] **Step 5: Replace the test README**

README must identify the repo as an unofficial Brave Android extensions overlay, link the approved spec and this plan, and show:

```bash
python3 -m unittest discover -s tests -v
./scripts/bootstrap.sh --print-plan /tmp/brave-ext-work
./scripts/build-android.sh --print-plan /tmp/brave-ext-work extensions
```

- [ ] **Step 6: Verify GREEN**

```bash
python3 -m unittest tests.test_config -v
bash -n scripts/lib/common.sh
```

- [ ] **Step 7: Commit**

```bash
git add README.md config scripts/lib/common.sh tests

git commit -m "chore: pin Brave Android extension build inputs"
```

---

### Task 2: Bootstrap the exact Brave/Chromium workspace

**Files:**
- Create: `scripts/bootstrap.sh`
- Create: `tests/test_bootstrap.py`

**Interface:** `scripts/bootstrap.sh [--print-plan] <work-root>` creates `<work-root>/src/brave` at the pinned commit and lets Brave initialize matching Chromium.

- [ ] **Step 1: Write failing print-plan test**

`tests/test_bootstrap.py` must invoke the script in a temporary directory and assert output contains:

```text
src/brave
f437ba81810858a15a961f13aab4fa24bb3ccce2
expected Brave version: 1.96.43
expected Chromium version: 153.0.8010.18
pnpm run init --target_os=android --target_arch=arm64
install-build-deps.sh --android
```

- [ ] **Step 2: Confirm RED**

```bash
python3 -m unittest tests.test_bootstrap -v
```

- [ ] **Step 3: Implement bootstrap**

Core implementation:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

PRINT_PLAN=false
[[ "${1:-}" == "--print-plan" ]] && { PRINT_PLAN=true; shift; }
[[ $# -eq 1 ]] || { echo "Usage: $0 [--print-plan] <work-root>" >&2; exit 2; }
WORK_ROOT="$(mkdir -p "$1" && cd "$1" && pwd)"
BRAVE_DIR="${WORK_ROOT}/src/brave"

if "$PRINT_PLAN"; then
  cat <<EOF
clone ${BRAVE_CORE_REPO} into ${BRAVE_DIR}
checkout ${BRAVE_CORE_REF}
expected Brave version: ${BRAVE_VERSION}
expected Chromium version: ${CHROMIUM_VERSION}
corepack enable
pnpm run init --target_os=android --target_arch=${APK_TARGET_ARCH}
${WORK_ROOT}/src/build/install-build-deps.sh --android
EOF
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

cd "${BRAVE_DIR}"
corepack enable
pnpm run init --target_os=android --target_arch="${APK_TARGET_ARCH}"
"${WORK_ROOT}/src/build/install-build-deps.sh" --android
```

- [ ] **Step 4: Verify unit/syntax tests**

```bash
chmod +x scripts/bootstrap.sh
python3 -m unittest tests.test_bootstrap -v
bash -n scripts/bootstrap.sh
```

- [ ] **Step 5: Verify one real bootstrap on a capable Linux machine**

```bash
./scripts/bootstrap.sh "$HOME/brave-ext-work"
git -C "$HOME/brave-ext-work/src/brave" rev-parse HEAD
test -f "$HOME/brave-ext-work/src/chrome/browser/extensions/desktop_android_extensions_browsertest.cc"
```

Expected commit: `f437ba81810858a15a961f13aab4fa24bb3ccce2`.

- [ ] **Step 6: Commit**

```bash
git add scripts/bootstrap.sh tests/test_bootstrap.py

git commit -m "build: add pinned Brave Android bootstrap"
```

---

### Task 3: Add deterministic overlay patching

**Files:**
- Create: `patches/README.md`
- Create: `scripts/apply-patches.sh`
- Create: `scripts/verify-patches.sh`
- Create: `tests/test_patch_scripts.py`

**Interfaces:**
- Numbered files `patches/NNNN-*.patch` apply lexicographically from Chromium `src/` using `patch -p1`.
- `OVERLAY_PATCH_DIR` is a test-only override for temporary patch directories.

- [ ] **Step 1: Write RED tests**

Use Python `tempfile` + `difflib.unified_diff` to create `0001-first.patch` and `0002-second.patch` for a fake `sample.txt`. Assert application order produces:

```text
first
second
```

Also test empty patch directory: apply exits 0 and prints `No overlay patches to apply.`.

- [ ] **Step 2: Implement dry-run verification**

`scripts/verify-patches.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PATCH_DIR="${OVERLAY_PATCH_DIR:-${PROJECT_ROOT}/patches}"
[[ $# -eq 1 ]] || { echo "Usage: $0 <chromium-src-root>" >&2; exit 2; }
SRC_ROOT="$(cd "$1" && pwd)"
mapfile -t patches < <(find "$PATCH_DIR" -maxdepth 1 -type f -name '[0-9][0-9][0-9][0-9]-*.patch' -print | sort)
[[ ${#patches[@]} -gt 0 ]] || { echo "No overlay patches to verify."; exit 0; }
for patch_file in "${patches[@]}"; do
  echo "Verifying $(basename "$patch_file")"
  patch --batch --forward --dry-run -p1 -d "$SRC_ROOT" < "$patch_file" >/dev/null
done
```

- [ ] **Step 3: Implement real application**

`scripts/apply-patches.sh` uses the same enumeration and, for every file:

```bash
patch --batch --forward --dry-run -p1 -d "$SRC_ROOT" < "$patch_file" >/dev/null
patch --batch --forward -p1 -d "$SRC_ROOT" < "$patch_file"
```

No patches: print exactly `No overlay patches to apply.` and exit 0.

- [ ] **Step 4: Document patch policy**

`patches/README.md` states naming, root path, dry-run-before-mutation, immediate failure on reject, and the rule that production patches require demonstrated compile/runtime evidence.

- [ ] **Step 5: Verify and commit**

```bash
chmod +x scripts/apply-patches.sh scripts/verify-patches.sh
python3 -m unittest tests.test_patch_scripts -v
bash -n scripts/apply-patches.sh scripts/verify-patches.sh

git add patches scripts/apply-patches.sh scripts/verify-patches.sh tests/test_patch_scripts.py

git commit -m "build: add deterministic Brave overlay patches"
```

---

### Task 4: Build baseline/extension APKs and collect artifacts

**Files:**
- Create: `scripts/build-android.sh`
- Create: `scripts/collect-artifacts.sh`
- Create: `tests/test_build_plan.py`

**Interfaces:**
- `scripts/build-android.sh [--print-plan] <work-root> <baseline|extensions>`.
- Extension mode obtains every `--gn` value through `extension_gn_cli_args()`.
- `scripts/collect-artifacts.sh <work-root> <artifact-dir>` discovers APKs without assuming a filename.

- [ ] **Step 1: Write RED command tests**

Assert baseline print-plan contains:

```text
pnpm run build Debug
-C BraveExtDebug
--target_os=android
--target_arch=arm64
--target_android_output_format=apk
--skip_signing
--use_remoteexec=false
```

and does not contain extension args. Assert extension print-plan additionally contains:

```text
--gn enable_desktop_android_extensions:true
--gn is_desktop_android:false
```

Create a fake `src/out/BraveExtDebug/.../fixture.apk`, run artifact collection, and assert `apk/fixture.apk` plus metadata are produced.

- [ ] **Step 2: Implement build script using GN config as source of truth**

Core extension-mode logic:

```bash
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
```

Print the shell-escaped command and stop in `--print-plan`; otherwise execute it from `<work-root>/src/brave` with `JAVA_OPTS=${JAVA_OPTS:--Xmx10G -Xms1G}`.

- [ ] **Step 3: Implement artifact collector**

Find all `*.apk` below `<work-root>/src/out/${BUILD_DIR}`, fail when none exist, copy them into `<artifact-dir>/apk/`, and create `build-metadata.txt` containing exact Brave ref/version, Chromium version, architecture, build dir, and overlay commit SHA.

- [ ] **Step 4: Verify tests/syntax**

```bash
chmod +x scripts/build-android.sh scripts/collect-artifacts.sh
python3 -m unittest tests.test_build_plan -v
bash -n scripts/build-android.sh scripts/collect-artifacts.sh
```

- [ ] **Step 5: M0 real baseline gate**

```bash
./scripts/build-android.sh "$HOME/brave-ext-work" baseline
rm -rf artifacts
./scripts/collect-artifacts.sh "$HOME/brave-ext-work" artifacts
find artifacts/apk -type f -name '*.apk' -print
```

Expected: at least one APK.

- [ ] **Step 6: Commit**

```bash
git add scripts/build-android.sh scripts/collect-artifacts.sh tests/test_build_plan.py

git commit -m "build: add reproducible Brave Android APK build"
```

---

### Task 5: Put M0 verification/build in GitHub Actions

**Files:**
- Create: `.github/workflows/verify.yml`
- Create: `.github/workflows/build-android-apk.yml`
- Create: `tests/test_workflows.py`
- Create: `docs/self-hosted-runner.md`

- [ ] **Step 1: Write RED workflow contract tests**

Assert `verify.yml` runs `python3 -m unittest discover -s tests -v`, `bash -n`, and `shellcheck`.

Assert build workflow:

- uses `workflow_dispatch`;
- has `runner` choices `ubuntu-24.04` and `self-hosted`;
- has `build_mode` choices `baseline` and `extensions`;
- calls bootstrap → verify patches → apply patches → build → collect artifacts;
- uploads with `actions/upload-artifact@v4`;
- contains neither `pull_request_target` nor a release signing secret nor `curl | sh`.

- [ ] **Step 2: Implement fast verify workflow**

Use `ubuntu-24.04`, `actions/checkout@v4`, Ubuntu `shellcheck`, then:

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/*.sh scripts/lib/*.sh
shellcheck scripts/*.sh scripts/lib/*.sh
```

- [ ] **Step 3: Implement manual APK workflow**

`workflow_dispatch` inputs:

```yaml
runner:
  required: true
  default: ubuntu-24.04
  type: choice
  options: [ubuntu-24.04, self-hosted]
build_mode:
  required: true
  default: baseline
  type: choice
  options: [baseline, extensions]
```

Job uses:

```yaml
runs-on: ${{ inputs.runner }}
```

and `actions/setup-node@v4` with `node-version: '24.16.0'`. Work root is `${{ runner.temp }}/brave-ext-work`. Do not cache Chromium in the first version.

- [ ] **Step 4: Document self-hosted build requirements**

`docs/self-hosted-runner.md` requires Linux x86_64, at least 150 GB free disk, recommends at least 32 GB RAM, and explains that hosted runners may hit resource limits. No signing material is required.

- [ ] **Step 5: Verify local workflow tests and trigger M0**

```bash
python3 -m unittest tests.test_workflows -v
python3 -m unittest discover -s tests -v
```

Trigger `Build Android APK` with `build_mode=baseline`. Try `ubuntu-24.04`; if the failure is specifically resource exhaustion, rerun the same immutable overlay commit on `self-hosted` rather than changing product code.

Successful artifact must contain `apk/*.apk` and `build-metadata.txt`.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows docs/self-hosted-runner.md tests/test_workflows.py

git commit -m "ci: build Brave Android APK in GitHub Actions"
```

M0 is complete here.

---

### Task 6: Verify the upstream Android extension build flags before source changes

**Files:**
- Create: `scripts/verify-extension-build.sh`
- Modify: `tests/test_build_plan.py`

**Interface:** `scripts/verify-extension-build.sh <work-root>` must prove generated GN values:

```text
enable_desktop_android_extensions = true
enable_extensions_core = true
is_desktop_android = false
```

- [ ] **Step 1: Write RED verification tests with a fake GN binary**

Create a fake executable at `src/buildtools/linux64/gn` that returns controlled text for `args ... --list=<name>`. Assert verifier accepts true/true/false and rejects true/false/false.

- [ ] **Step 2: Implement verifier**

Use:

```bash
GN="${WORK_ROOT}/src/buildtools/linux64/gn"
OUT="${WORK_ROOT}/src/out/${BUILD_DIR}"
```

For each name call:

```bash
"$GN" args "$OUT" --list="$name"
```

Require the returned listing to show the expected current boolean value, print all captured output to CI logs, and fail otherwise.

- [ ] **Step 3: Generate extension build files only**

From `src/brave` construct arguments through `extension_gn_cli_args()` and run the same Debug Android build as Task 4 with `--prepare_only` appended.

Then:

```bash
./scripts/verify-extension-build.sh "$HOME/brave-ext-work"
```

- [ ] **Step 4: Attempt the full extension-enabled APK with zero production patches**

```bash
./scripts/build-android.sh "$HOME/brave-ext-work" extensions
./scripts/verify-extension-build.sh "$HOME/brave-ext-work"
```

Expected: successful link and APK. If compilation/linking fails, preserve the first concrete error and use `superpowers:systematic-debugging` before authoring a production patch. Any new patch must have a regression test tied to that failure.

- [ ] **Step 5: Verify and commit**

```bash
chmod +x scripts/verify-extension-build.sh
python3 -m unittest tests.test_build_plan -v
bash -n scripts/verify-extension-build.sh

git add scripts/verify-extension-build.sh tests/test_build_plan.py

git commit -m "build: verify Chromium extension core on Android"
```

---

### Task 7: Add the deterministic Manifest V3 fixture

**Files:**
- Create: `fixtures/test-extension/manifest.json`
- Create: `fixtures/test-extension/background.js`
- Create: `fixtures/test-extension/content_script.js`
- Create: `fixtures/test-extension/popup.html`
- Create: `fixtures/test-extension/popup.js`
- Create: `tests/test_fixture.py`

**Stable fixture contract:** name `Brave Android Extensions MVP Fixture`; version `0.1.0`; marker id `brave-android-extension-fixture`; marker text `fixture-content-script-ok`; message `fixture-ping` → `{reply: 'fixture-pong'}`; storage key `fixtureSeen`.

- [ ] **Step 1: Write RED fixture tests**

Parse `manifest.json` and assert MV3, exact name/version, `storage`, service worker, popup, and `http://match.test/*`. Assert source strings above occur exactly where expected.

- [ ] **Step 2: Create fixture files**

`manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "Brave Android Extensions MVP Fixture",
  "version": "0.1.0",
  "permissions": ["storage"],
  "host_permissions": ["http://match.test/*"],
  "background": {"service_worker": "background.js"},
  "action": {"default_popup": "popup.html"},
  "content_scripts": [{
    "matches": ["http://match.test/*"],
    "js": ["content_script.js"],
    "run_at": "document_idle"
  }]
}
```

`content_script.js`:

```javascript
const marker = document.createElement('div')
marker.id = 'brave-android-extension-fixture'
marker.textContent = 'fixture-content-script-ok'
document.documentElement.appendChild(marker)
```

`background.js`:

```javascript
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message !== 'fixture-ping') return false
  chrome.storage.local.set({ fixtureSeen: true }).then(() => {
    sendResponse({ reply: 'fixture-pong' })
  })
  return true
})
```

`popup.html`:

```html
<!doctype html>
<html><body><output id="state">unknown</output><script src="popup.js"></script></body></html>
```

`popup.js`:

```javascript
chrome.storage.local.get('fixtureSeen').then(({ fixtureSeen }) => {
  document.getElementById('state').textContent = fixtureSeen ? 'seen' : 'not-seen'
})
```

- [ ] **Step 3: Verify and commit**

```bash
python3 -m unittest tests.test_fixture -v

git add fixtures tests/test_fixture.py

git commit -m "test: add Android MV3 extension fixture"
```

---

### Task 8: Stage fixture data and patch the exact Chromium 153 browser test

**Files:**
- Create: `scripts/stage-test-fixture.sh`
- Create: `patches/0001-brave-android-extension-fixture-test.patch`
- Modify: `tests/test_patch_scripts.py`

**Exact upstream file:** `chrome/browser/extensions/desktop_android_extensions_browsertest.cc` at Chromium `153.0.8010.18`.

- [ ] **Step 1: Write RED staging test**

Create a fake source root with `chrome/test/data/extensions`, run `stage-test-fixture.sh`, and byte-compare all five staged fixture files with the overlay originals.

- [ ] **Step 2: Implement staging**

`scripts/stage-test-fixture.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
[[ $# -eq 1 ]] || { echo "Usage: $0 <chromium-src-root>" >&2; exit 2; }
SRC_ROOT="$(cd "$1" && pwd)"
SOURCE="${PROJECT_ROOT}/fixtures/test-extension"
DEST="${SRC_ROOT}/chrome/test/data/extensions/brave_android_mvp"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "${SOURCE}/." "$DEST/"
```

- [ ] **Step 3: Make the exact test-only source edit in a clean pinned Chromium tree**

Add these includes to `chrome/browser/extensions/desktop_android_extensions_browsertest.cc`:

```cpp
#include "base/path_service.h"
#include "chrome/common/chrome_paths.h"
```

Add this test after the existing `ContentScriptInjection` test:

```cpp
IN_PROC_BROWSER_TEST_F(DesktopAndroidExtensionsBrowserTest,
                       BraveMvpFixtureContentScript) {
  base::FilePath test_data_dir;
  ASSERT_TRUE(base::PathService::Get(chrome::DIR_TEST_DATA, &test_data_dir));
  const base::FilePath fixture_dir =
      test_data_dir.AppendASCII("extensions").AppendASCII("brave_android_mvp");

  scoped_refptr<const Extension> extension =
      LoadExtensionFromDirectory(fixture_dir);
  ASSERT_TRUE(extension);
  EXPECT_EQ("Brave Android Extensions MVP Fixture", extension->name());

  UserScriptManager* user_script_manager =
      ExtensionSystem::Get(GetBrowserContext())->user_script_manager();
  ExtensionUserScriptLoader* user_script_loader =
      user_script_manager->GetUserScriptLoaderForExtension(extension->id());
  if (!user_script_loader->HasLoadedScripts()) {
    ContentScriptLoadWaiter waiter(user_script_loader);
    waiter.Wait();
  }

  const GURL match_test =
      embedded_test_server()->GetURL("match.test", "/title1.html");
  ASSERT_TRUE(content::NavigateToURL(GetActiveWebContents(), match_test));
  EXPECT_EQ(
      "fixture-content-script-ok",
      content::EvalJs(
          GetActiveWebContents(),
          "document.getElementById('brave-android-extension-fixture').textContent"));
}
```

All types used except the two newly included path helpers are already included/used by the pinned file.

- [ ] **Step 4: Generate the patch from the Chromium root**

After editing:

```bash
cd "$HOME/brave-ext-work/src"
git diff -- chrome/browser/extensions/desktop_android_extensions_browsertest.cc \
  > /path/to/overlay/patches/0001-brave-android-extension-fixture-test.patch
git checkout -- chrome/browser/extensions/desktop_android_extensions_browsertest.cc
```

The saved patch must modify exactly one Chromium file.

- [ ] **Step 5: Verify/apply/stage from a clean tree**

```bash
./scripts/verify-patches.sh "$HOME/brave-ext-work/src"
./scripts/apply-patches.sh "$HOME/brave-ext-work/src"
./scripts/stage-test-fixture.sh "$HOME/brave-ext-work/src"
test -f "$HOME/brave-ext-work/src/chrome/test/data/extensions/brave_android_mvp/manifest.json"
```

- [ ] **Step 6: Verify overlay tests and commit**

```bash
chmod +x scripts/stage-test-fixture.sh
python3 -m unittest tests.test_patch_scripts tests.test_fixture -v
bash -n scripts/stage-test-fixture.sh

git add scripts/stage-test-fixture.sh patches/0001-brave-android-extension-fixture-test.patch tests/test_patch_scripts.py

git commit -m "test: wire MV3 fixture into Chromium Android browser tests"
```

---

### Task 9: Run the M1 runtime gate on Android x86

**Files:**
- Create: `scripts/test-extension-runtime.sh`
- Create: `tests/test_runtime_test_plan.py`
- Modify: `docs/self-hosted-runner.md`
- Create: `docs/compatibility.md`

**Interface:** `scripts/test-extension-runtime.sh [--print-plan] <work-root>` runs Chromium suite `browser_tests` with a focused extension filter.

- [ ] **Step 1: Write RED runtime-plan test**

Assert output contains:

```text
pnpm run test browser_tests
--target_os=android
--target_arch=x86
--manual_android_test_device
--gn enable_desktop_android_extensions:true
--gn is_desktop_android:false
DesktopAndroidExtensionsBrowserTest.BraveMvpFixtureContentScript
DesktopAndroidExtensionsBrowserTest.ServiceWorkerBasedExtension
DesktopAndroidExtensionsBrowserTest.ContentScriptInjection
DesktopAndroidExtensionsBrowserTest.StorageApiTestStorageAreaLocal
DesktopAndroidExtensionsBrowserTest.MessagePassing
```

- [ ] **Step 2: Implement runtime script**

Always stage the fixture first. Build this exact filter:

```bash
FILTER="DesktopAndroidExtensionsBrowserTest.BraveMvpFixtureContentScript:DesktopAndroidExtensionsBrowserTest.ServiceWorkerBasedExtension:DesktopAndroidExtensionsBrowserTest.ContentScriptInjection:DesktopAndroidExtensionsBrowserTest.StorageApiTestStorageAreaLocal:DesktopAndroidExtensionsBrowserTest.MessagePassing"
```

Build GN CLI args using `extension_gn_cli_args()` and execute from `<work-root>/src/brave`:

```bash
pnpm run test browser_tests \
  --target_os=android \
  --target_arch=x86 \
  --manual_android_test_device \
  --gn enable_desktop_android_extensions:true \
  --gn is_desktop_android:false \
  --filter="$FILTER"
```

The implementation must construct the two `--gn` pairs from config; the literal command above documents the expected expansion.

- [ ] **Step 3: Document emulator preflight**

Extend `docs/self-hosted-runner.md`: Android SDK/adb on PATH, x86 emulator image installed, emulator booted before job start, and exactly one usable adb target for initial M1.

Preflight:

```bash
adb devices
adb shell getprop sys.boot_completed
```

Expected boot value: `1`.

- [ ] **Step 4: Execute the focused tests**

```bash
./scripts/test-extension-runtime.sh "$HOME/brave-ext-work"
```

All five tests must pass. If a pinned test name/target differs at execution time, inspect the actual generated test list and correct both implementation and contract test in the same commit; do not drop a capability from the M1 gate.

- [ ] **Step 5: Record only proven compatibility**

Create `docs/compatibility.md`:

```markdown
| Capability | M1 status | Evidence |
| --- | --- | --- |
| Manifest V3 unpacked load | Proven | Chromium Android extension browser tests + fixture |
| Content scripts | Proven | BraveMvpFixtureContentScript + ContentScriptInjection |
| MV3 service worker | Proven | ServiceWorkerBasedExtension |
| storage.local | Proven | StorageApiTestStorageAreaLocal |
| runtime messaging | Proven | MessagePassing |
| General CRX install | Not implemented | M2 |
| Mobile extension manager | Not implemented | M2 |
| Action popup UI | Not implemented | M3 |
| Chrome Web Store | Not implemented | M4 |
```

- [ ] **Step 6: Verify and commit**

```bash
chmod +x scripts/test-extension-runtime.sh
python3 -m unittest tests.test_runtime_test_plan tests.test_fixture -v
bash -n scripts/test-extension-runtime.sh

git add scripts/test-extension-runtime.sh tests/test_runtime_test_plan.py docs/self-hosted-runner.md docs/compatibility.md

git commit -m "test: verify Android Chromium extension runtime"
```

---

### Task 10: Gate extension APK/runtime in GitHub Actions

**Files:**
- Create: `.github/workflows/runtime-extension-tests.yml`
- Modify: `.github/workflows/build-android-apk.yml`
- Modify: `tests/test_workflows.py`
- Modify: `README.md`
- Modify: `docs/compatibility.md`

- [ ] **Step 1: Extend RED workflow tests**

Require runtime workflow to be `workflow_dispatch`, `runs-on: self-hosted`, use only GitHub-maintained setup/checkout actions, run adb preflight, bootstrap, verify/apply patches, and `test-extension-runtime.sh`. Require APK workflow default mode to become `extensions`.

- [ ] **Step 2: Create runtime workflow**

Use self-hosted runner with pre-booted emulator. Steps:

```text
checkout overlay
setup Node 24.16.0
corepack enable
adb devices
verify sys.boot_completed == 1
bootstrap ${runner.temp}/brave-ext-work
verify patches
apply patches
run test-extension-runtime.sh
```

Do not hide emulator provisioning inside the repository during M1.

- [ ] **Step 3: Promote extension APK as default development build**

Change build workflow `build_mode` default to `extensions`. After an extension build call:

```bash
./scripts/verify-extension-build.sh "$WORK_ROOT"
```

Baseline remains selectable for diagnostics.

- [ ] **Step 4: Update README with exact M0-M1 flow**

```bash
python3 -m unittest discover -s tests -v
./scripts/bootstrap.sh "$HOME/brave-ext-work"
./scripts/verify-patches.sh "$HOME/brave-ext-work/src"
./scripts/apply-patches.sh "$HOME/brave-ext-work/src"
./scripts/build-android.sh "$HOME/brave-ext-work" extensions
./scripts/verify-extension-build.sh "$HOME/brave-ext-work"
./scripts/test-extension-runtime.sh "$HOME/brave-ext-work"
```

State explicitly that M1 proves runtime only; it does not yet provide arbitrary CRX or Chrome Web Store installation.

- [ ] **Step 5: Full local verification**

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/*.sh scripts/lib/*.sh
shellcheck scripts/*.sh scripts/lib/*.sh
```

- [ ] **Step 6: Run both GitHub Actions gates on the same overlay commit**

1. `Build Android APK`: `runner=self-hosted`, `build_mode=extensions`. Require uploaded APK + metadata.
2. `Runtime Extension Tests`: require all five focused tests green.

- [ ] **Step 7: Record immutable evidence and commit**

Add successful overlay commit SHA and Actions run IDs to `docs/compatibility.md`, then:

```bash
git add .github/workflows README.md tests/test_workflows.py docs/compatibility.md

git commit -m "ci: gate Brave Android extension runtime"
```

---

## M0-M1 completion gate

Do not start M2 until all items are true on one overlay commit:

```text
[ ] Python overlay tests pass
[ ] bash -n and shellcheck pass
[ ] Brave Core pin resolves to 1.96.43 / Chromium 153.0.8010.18
[ ] baseline ARM64 debug APK builds
[ ] extension ARM64 debug APK builds
[ ] generated GN proves enable_desktop_android_extensions=true
[ ] generated GN proves enable_extensions_core=true
[ ] generated GN proves is_desktop_android=false
[ ] extension APK + metadata are uploaded by GitHub Actions
[ ] BraveMvpFixtureContentScript passes on Android x86
[ ] ServiceWorkerBasedExtension passes on Android x86
[ ] ContentScriptInjection passes on Android x86
[ ] StorageApiTestStorageAreaLocal passes on Android x86
[ ] MessagePassing passes on Android x86
[ ] docs/compatibility.md claims only tested capabilities
```

When green, write the separate M2 plan for the native Extensions manager and validated local CRX installation. M3 handles action/popup UI, M4 Chrome Web Store integration, and M5 compatibility hardening.
