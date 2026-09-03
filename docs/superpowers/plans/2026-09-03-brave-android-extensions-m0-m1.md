# Brave Android Extensions M0-M1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible Brave-derived Android debug APK with Chromium's upstream Android extension core enabled and prove that a deterministic Manifest V3 fixture extension executes on Android.

**Architecture:** This repository remains a small overlay/build-orchestration project. It pins a Brave Core revision, bootstraps Brave/Chromium into an external work directory, applies numbered root-relative patches, passes Android extension GN arguments without enabling the full Desktop Android form factor, builds an ARM64 APK, and runs extension runtime browser tests on an x86 Android emulator/self-hosted runner.

**Tech Stack:** Bash, Python 3 standard library `unittest`, GitHub Actions, Brave Core 1.96.43, Chromium 153.0.8010.18, Node 24.x, pnpm 11.x, GN/Ninja/Siso via Brave build tooling, Chromium extensions framework, Android browser tests.

**Spec:** `docs/superpowers/specs/2026-09-03-brave-android-extensions-design.md`

## Global Constraints

- Pin Brave Core to commit `f437ba81810858a15a961f13aab4fa24bb3ccce2` (`1.96.43`) and verify its Chromium tag is exactly `153.0.8010.18` before building.
- Use Node `>=24.16.0 <25.0.0` and pnpm `>=11.11.0`, matching the pinned Brave Core `package.json`.
- Keep standard mobile Android behavior: `is_desktop_android=false`.
- Enable the upstream extension path with `enable_desktop_android_extensions=true`; do not recreate Brave's historical 2020 Android-extension patch set.
- Do not broadly remove `IS_ANDROID`/`is_android` guards. Any source patch must be narrowly justified by a concrete build/runtime failure.
- M0-M1 cover build reproducibility and extension runtime only. Extension manager UI, arbitrary CRX installation, extension popup UX, Chrome Web Store installation, release signing, and public distribution are outside this plan.
- APK artifact target is `arm64`; runtime browser-test target is `x86` on an Android emulator.
- Development artifacts are unsigned/debug builds and must not be presented as an official Brave release.
- No release/private signing keys are committed to the repository.
- GitHub-hosted runners are best-effort because a Chromium build can exceed their disk/RAM/time limits. The same workflow must support a `self-hosted` runner.
- Use only GitHub-maintained actions in the initial workflow (`actions/checkout`, `actions/setup-node`, `actions/upload-artifact`).
- Every shell script uses `set -euo pipefail`, validates required inputs, and supports a non-destructive `--print-plan` mode where specified.
- M2-M5 are implemented only after the M1 runtime test is green and receive separate implementation plans.

---

## File map

Files created or modified by this plan:

```text
README.md                                      project entry point and build/run instructions
config/brave-version.env                       authoritative upstream/version/build pin
config/android-extension-args.gn              reviewed GN values for extension builds
patches/README.md                              patch contract and numbering rules
patches/0001-brave-android-extension-fixture-test.patch
                                                first narrow Chromium test patch
fixtures/test-extension/manifest.json          deterministic MV3 fixture manifest
fixtures/test-extension/background.js          service worker/message/storage fixture
fixtures/test-extension/content_script.js      deterministic page marker
fixtures/test-extension/popup.html              action popup fixture page
fixtures/test-extension/popup.js                reads fixture storage state
scripts/lib/common.sh                          shared config/path validation
scripts/bootstrap.sh                           checkout + Brave Android initialization
scripts/apply-patches.sh                       deterministic patch application
scripts/verify-patches.sh                      non-mutating patch dry-run
scripts/stage-test-fixture.sh                   copies fixture into Chromium test data
scripts/build-android.sh                       baseline/extension APK build entry point
scripts/collect-artifacts.sh                   APK + metadata collection
scripts/verify-extension-build.sh              checks generated GN extension state
scripts/test-extension-runtime.sh              focused Android extension browser tests
tests/__init__.py                              unittest package marker
tests/test_config.py                           configuration contract
tests/test_bootstrap.py                        bootstrap command-plan contract
tests/test_patch_scripts.py                    patch order/apply/dry-run contract
tests/test_build_plan.py                       build and artifact collection contract
tests/test_fixture.py                          fixture manifest/source contract
tests/test_runtime_test_plan.py                runtime-test command contract
tests/test_workflows.py                        CI workflow contract
.github/workflows/verify.yml                   fast overlay validation
.github/workflows/build-android-apk.yml         manual APK build workflow
.github/workflows/runtime-extension-tests.yml   self-hosted emulator runtime test workflow
docs/compatibility.md                          M1 supported/proven extension capabilities
docs/self-hosted-runner.md                     machine/emulator requirements
```

`patches/0001-...` is deliberately a test-only patch. If simply setting the current upstream GN arguments is sufficient for M1, M1 lands without production Chromium source modifications. Production patches begin only when a demonstrated compile/runtime failure requires one.

---

### Task 1: Lock the upstream/build contract

**Files:**
- Create: `config/brave-version.env`
- Create: `config/android-extension-args.gn`
- Create: `scripts/lib/common.sh`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: none.
- Produces: shell variables `BRAVE_CORE_REPO`, `BRAVE_CORE_REF`, `BRAVE_VERSION`, `CHROMIUM_VERSION`, `APK_TARGET_ARCH`, `TEST_TARGET_ARCH`, `BUILD_DIR`; function `load_project_config()` in `scripts/lib/common.sh`.

- [ ] **Step 1: Write the configuration contract test**

Create `tests/test_config.py`:

```python
from pathlib import Path
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
    def test_pinned_brave_and_chromium_versions(self) -> None:
        values = parse_env(ROOT / "config" / "brave-version.env")
        self.assertEqual(values["BRAVE_CORE_REPO"], "https://github.com/brave/brave-core.git")
        self.assertEqual(values["BRAVE_CORE_REF"], "f437ba81810858a15a961f13aab4fa24bb3ccce2")
        self.assertEqual(values["BRAVE_VERSION"], "1.96.43")
        self.assertEqual(values["CHROMIUM_VERSION"], "153.0.8010.18")
        self.assertEqual(values["APK_TARGET_ARCH"], "arm64")
        self.assertEqual(values["TEST_TARGET_ARCH"], "x86")
        self.assertEqual(values["BUILD_DIR"], "BraveExtDebug")

    def test_extension_args_keep_mobile_form_factor(self) -> None:
        args = (ROOT / "config" / "android-extension-args.gn").read_text(encoding="utf-8")
        self.assertIn("enable_desktop_android_extensions = true", args)
        self.assertIn("is_desktop_android = false", args)


if __name__ == "__main__":
    unittest.main()
```

Create empty `tests/__init__.py`.

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_config -v
```

Expected: errors because `config/brave-version.env` and `config/android-extension-args.gn` do not exist.

- [ ] **Step 3: Add the authoritative config files**

Create `config/brave-version.env`:

```dotenv
BRAVE_CORE_REPO=https://github.com/brave/brave-core.git
BRAVE_CORE_REF=f437ba81810858a15a961f13aab4fa24bb3ccce2
BRAVE_VERSION=1.96.43
CHROMIUM_VERSION=153.0.8010.18
APK_TARGET_ARCH=arm64
TEST_TARGET_ARCH=x86
BUILD_DIR=BraveExtDebug
```

Create `config/android-extension-args.gn`:

```gn
enable_desktop_android_extensions = true
is_desktop_android = false
```

- [ ] **Step 4: Add shared shell configuration loading**

Create `scripts/lib/common.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

load_project_config() {
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/config/brave-version.env"

  local required=(
    BRAVE_CORE_REPO BRAVE_CORE_REF BRAVE_VERSION CHROMIUM_VERSION
    APK_TARGET_ARCH TEST_TARGET_ARCH BUILD_DIR
  )
  local name
  for name in "${required[@]}"; do
    if [[ -z "${!name:-}" ]]; then
      printf 'Missing required project variable: %s\n' "$name" >&2
      return 1
    fi
  done
}

require_work_root() {
  if [[ $# -ne 1 || -z "$1" ]]; then
    printf 'A work root path is required.\n' >&2
    return 2
  fi
}
```

- [ ] **Step 5: Replace the test README with a project entry point**

Replace `README.md` with a concise description naming the project as an unofficial development overlay, linking the design/spec and stating that M0-M1 targets an ARM64 debug APK plus x86 emulator extension tests. Include these exact quick checks:

```bash
python3 -m unittest discover -s tests -v
./scripts/bootstrap.sh --print-plan /tmp/brave-ext-work
./scripts/build-android.sh --print-plan /tmp/brave-ext-work extensions
```

Do not add public release/download claims at this stage.

- [ ] **Step 6: Run the test and shell syntax checks**

Run:

```bash
python3 -m unittest tests.test_config -v
bash -n scripts/lib/common.sh
```

Expected: both succeed.

- [ ] **Step 7: Commit**

```bash
git add README.md config scripts/lib/common.sh tests

git commit -m "chore: pin Brave Android extension build inputs"
```

---

### Task 2: Build a deterministic Brave bootstrapper

**Files:**
- Create: `scripts/bootstrap.sh`
- Create: `tests/test_bootstrap.py`

**Interfaces:**
- Consumes: `load_project_config()` and variables from Task 1.
- Produces: CLI `scripts/bootstrap.sh [--print-plan] <work-root>`; initialized Brave source at `<work-root>/src/brave` and Chromium source at `<work-root>/src`.

- [ ] **Step 1: Write a print-plan test before implementing bootstrap**

Create `tests/test_bootstrap.py`:

```python
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapPlanTest(unittest.TestCase):
    def test_print_plan_is_pinned_and_uses_brave_supported_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [str(ROOT / "scripts" / "bootstrap.sh"), "--print-plan", tmp],
                check=True,
                text=True,
                capture_output=True,
            )
        out = result.stdout
        self.assertIn("src/brave", out)
        self.assertIn("f437ba81810858a15a961f13aab4fa24bb3ccce2", out)
        self.assertIn("pnpm run init --target_os=android --target_arch=arm64", out)
        self.assertIn("install-build-deps.sh --android", out)
        self.assertIn("expected Brave version: 1.96.43", out)
        self.assertIn("expected Chromium version: 153.0.8010.18", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and verify failure**

```bash
python3 -m unittest tests.test_bootstrap -v
```

Expected: failure because `scripts/bootstrap.sh` does not exist.

- [ ] **Step 3: Implement `--print-plan` and real bootstrap**

Create `scripts/bootstrap.sh` with this behavior:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

PRINT_PLAN=false
if [[ "${1:-}" == "--print-plan" ]]; then
  PRINT_PLAN=true
  shift
fi
require_work_root "$@"
WORK_ROOT="$(mkdir -p "$1" && cd "$1" && pwd)"
BRAVE_DIR="${WORK_ROOT}/src/brave"

print_plan() {
  cat <<EOF
work root: ${WORK_ROOT}
clone: ${BRAVE_CORE_REPO} -> ${BRAVE_DIR}
checkout: ${BRAVE_CORE_REF}
expected Brave version: ${BRAVE_VERSION}
expected Chromium version: ${CHROMIUM_VERSION}
command: corepack enable
command: pnpm install --frozen-lockfile
command: pnpm run init --target_os=android --target_arch=${APK_TARGET_ARCH}
command: ${WORK_ROOT}/src/build/install-build-deps.sh --android
EOF
}

if "$PRINT_PLAN"; then
  print_plan
  exit 0
fi

mkdir -p "${WORK_ROOT}/src"
if [[ ! -d "${BRAVE_DIR}/.git" ]]; then
  git clone "${BRAVE_CORE_REPO}" "${BRAVE_DIR}"
fi

git -C "${BRAVE_DIR}" fetch --tags origin
git -C "${BRAVE_DIR}" checkout --detach "${BRAVE_CORE_REF}"

python3 - "${BRAVE_DIR}/package.json" "${BRAVE_VERSION}" "${CHROMIUM_VERSION}" <<'PY'
import json
from pathlib import Path
import sys

package = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_brave, expected_chromium = sys.argv[2], sys.argv[3]
actual_brave = package["version"]
actual_chromium = package["config"]["projects"]["chrome"]["tag"]
if actual_brave != expected_brave:
    raise SystemExit(f"Brave version mismatch: {actual_brave} != {expected_brave}")
if actual_chromium != expected_chromium:
    raise SystemExit(f"Chromium version mismatch: {actual_chromium} != {expected_chromium}")
PY

cd "${BRAVE_DIR}"
corepack enable
pnpm install --frozen-lockfile
pnpm run init --target_os=android --target_arch="${APK_TARGET_ARCH}"
"${WORK_ROOT}/src/build/install-build-deps.sh" --android
```

The version verification runs before the multi-gigabyte initialization so an accidental pin mismatch fails quickly.

- [ ] **Step 4: Run unit/syntax tests**

```bash
chmod +x scripts/bootstrap.sh
python3 -m unittest tests.test_bootstrap -v
bash -n scripts/bootstrap.sh
```

Expected: pass.

- [ ] **Step 5: Validate real bootstrap on a Linux build machine**

Run on a machine with enough disk space for Chromium:

```bash
./scripts/bootstrap.sh "$HOME/brave-ext-work"
```

Expected after completion:

```bash
git -C "$HOME/brave-ext-work/src/brave" rev-parse HEAD
# f437ba81810858a15a961f13aab4fa24bb3ccce2

test -d "$HOME/brave-ext-work/src/chrome"
```

If the host dependency script requires root privileges, configure the self-hosted runner account with the prerequisite packages before rerunning rather than adding an unattended sudo password to CI.

- [ ] **Step 6: Commit**

```bash
git add scripts/bootstrap.sh tests/test_bootstrap.py

git commit -m "build: add pinned Brave Android bootstrap"
```

---

### Task 3: Add the root-relative overlay patch framework

**Files:**
- Create: `patches/README.md`
- Create: `scripts/apply-patches.sh`
- Create: `scripts/verify-patches.sh`
- Create: `tests/test_patch_scripts.py`

**Interfaces:**
- Consumes: project `patches/NNNN-*.patch` files.
- Produces: `scripts/apply-patches.sh <chromium-src-root>` and `scripts/verify-patches.sh <chromium-src-root>`; patches apply lexicographically from the Chromium source root so they may address both Chromium paths and `brave/...` paths under `src`.

- [ ] **Step 1: Write patch ordering and no-patch tests**

Create `tests/test_patch_scripts.py`. The test must create a temporary fake source tree with `sample.txt`, generate two unified patches named `0001-first.patch` and `0002-second.patch` in a temporary copy of the repository patch directory, and assert that applying them produces `first\nsecond\n`. Also add a test that an empty patch directory exits zero and prints `No overlay patches to apply.`.

Use this helper in the test to create valid patches:

```python
def patch_text(old: str, new: str) -> str:
    import difflib
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="a/sample.txt",
            tofile="b/sample.txt",
        )
    )
```

The test invokes the scripts with environment variable `OVERLAY_PATCH_DIR` pointing at its temporary patch directory. This environment override exists only to make the patch engine independently testable.

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_patch_scripts -v
```

Expected: failure because the scripts do not exist.

- [ ] **Step 3: Implement non-mutating verification**

Create `scripts/verify-patches.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PATCH_DIR="${OVERLAY_PATCH_DIR:-${PROJECT_ROOT}/patches}"

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s <chromium-src-root>\n' "$0" >&2
  exit 2
fi
SRC_ROOT="$(cd "$1" && pwd)"

mapfile -t patches < <(find "${PATCH_DIR}" -maxdepth 1 -type f -name '[0-9][0-9][0-9][0-9]-*.patch' -print | sort)
if [[ ${#patches[@]} -eq 0 ]]; then
  printf 'No overlay patches to verify.\n'
  exit 0
fi

for patch_file in "${patches[@]}"; do
  printf 'Verifying %s\n' "$(basename "$patch_file")"
  patch --batch --forward --dry-run -p1 -d "${SRC_ROOT}" < "$patch_file" >/dev/null
done
```

- [ ] **Step 4: Implement deterministic application**

Create `scripts/apply-patches.sh` with the same ordered enumeration, but for each patch first run the dry-run and then the real application:

```bash
patch --batch --forward --dry-run -p1 -d "${SRC_ROOT}" < "$patch_file" >/dev/null
patch --batch --forward -p1 -d "${SRC_ROOT}" < "$patch_file"
```

When no numbered patches exist, print exactly `No overlay patches to apply.` and exit zero.

- [ ] **Step 5: Document the patch contract**

Create `patches/README.md` stating:

- names must match `NNNN-description.patch`;
- patches are applied from Chromium `src/` with `-p1`;
- every patch must pass a clean dry-run before mutation;
- a failed patch aborts immediately;
- production Chromium changes require a failing build/runtime test demonstrating why the patch is necessary;
- test-only fixture integration is allowed as patch `0001`.

- [ ] **Step 6: Run tests/syntax checks**

```bash
chmod +x scripts/apply-patches.sh scripts/verify-patches.sh
python3 -m unittest tests.test_patch_scripts -v
bash -n scripts/apply-patches.sh scripts/verify-patches.sh
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add patches scripts/apply-patches.sh scripts/verify-patches.sh tests/test_patch_scripts.py

git commit -m "build: add deterministic Brave overlay patches"
```

---

### Task 4: Make M0 build and artifact collection executable

**Files:**
- Create: `scripts/build-android.sh`
- Create: `scripts/collect-artifacts.sh`
- Create: `tests/test_build_plan.py`

**Interfaces:**
- Consumes: initialized work root from Task 2; extension GN config from Task 1.
- Produces: `scripts/build-android.sh [--print-plan] <work-root> <baseline|extensions>` and `scripts/collect-artifacts.sh <work-root> <artifact-dir>`.

- [ ] **Step 1: Write command-plan tests**

Create `tests/test_build_plan.py` with two subprocess tests. For `baseline`, assert output contains:

```text
pnpm run build Debug
--target_os=android
--target_arch=arm64
--target_android_output_format=apk
--skip_signing
```

and does not contain `enable_desktop_android_extensions:true`.

For `extensions`, additionally assert:

```text
--gn enable_desktop_android_extensions:true
--gn is_desktop_android:false
```

Also create a temporary fake work root containing `src/out/BraveExtDebug/apks/test.apk`, invoke `collect-artifacts.sh`, and assert the APK is copied and metadata contains the pinned Brave ref and Chromium version.

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_build_plan -v
```

Expected: failure because build/collect scripts do not exist.

- [ ] **Step 3: Implement the build entry point**

Create `scripts/build-android.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
load_project_config

PRINT_PLAN=false
if [[ "${1:-}" == "--print-plan" ]]; then
  PRINT_PLAN=true
  shift
fi
if [[ $# -ne 2 ]]; then
  printf 'Usage: %s [--print-plan] <work-root> <baseline|extensions>\n' "$0" >&2
  exit 2
fi
WORK_ROOT="$(cd "$1" && pwd)"
MODE="$2"
BRAVE_DIR="${WORK_ROOT}/src/brave"

case "$MODE" in
  baseline) extra_gn=() ;;
  extensions)
    extra_gn=(
      --gn enable_desktop_android_extensions:true
      --gn is_desktop_android:false
    )
    ;;
  *) printf 'Unknown build mode: %s\n' "$MODE" >&2; exit 2 ;;
esac

command=(
  pnpm run build Debug
  -C "${BUILD_DIR}"
  --target_os=android
  --target_arch="${APK_TARGET_ARCH}"
  --target_android_output_format=apk
  --skip_signing
  --use_remoteexec=false
  "${extra_gn[@]}"
)

printf 'JAVA_OPTS=-Xmx10G -Xms1G '
printf '%q ' "${command[@]}"
printf '\n'
if "$PRINT_PLAN"; then
  exit 0
fi

cd "${BRAVE_DIR}"
export JAVA_OPTS="${JAVA_OPTS:--Xmx10G -Xms1G}"
"${command[@]}"
```

- [ ] **Step 4: Implement artifact collection without assuming an APK filename**

Create `scripts/collect-artifacts.sh` to:

1. load config;
2. find `*.apk` recursively below `<work-root>/src/out/${BUILD_DIR}`;
3. fail if none exist;
4. copy APKs into the requested artifact directory under `apk/`;
5. write `build-metadata.txt` containing:

```text
brave_core_ref=f437ba81810858a15a961f13aab4fa24bb3ccce2
brave_version=1.96.43
chromium_version=153.0.8010.18
apk_target_arch=arm64
build_dir=BraveExtDebug
```

When executed from a git checkout, append `overlay_commit=$(git -C "$PROJECT_ROOT" rev-parse HEAD)`.

- [ ] **Step 5: Run unit/syntax tests**

```bash
chmod +x scripts/build-android.sh scripts/collect-artifacts.sh
python3 -m unittest tests.test_build_plan -v
bash -n scripts/build-android.sh scripts/collect-artifacts.sh
```

Expected: pass.

- [ ] **Step 6: Prove the unchanged M0 baseline builds**

On the initialized Linux work root:

```bash
./scripts/build-android.sh "$HOME/brave-ext-work" baseline
rm -rf artifacts
./scripts/collect-artifacts.sh "$HOME/brave-ext-work" artifacts
find artifacts/apk -type f -name '*.apk' -print
```

Expected: at least one debug APK path is printed. This baseline gate separates general Brave build failures from extension-specific failures.

- [ ] **Step 7: Commit**

```bash
git add scripts/build-android.sh scripts/collect-artifacts.sh tests/test_build_plan.py

git commit -m "build: add reproducible Brave Android APK build"
```

---

### Task 5: Put M0 verification and APK builds in GitHub Actions

**Files:**
- Create: `.github/workflows/verify.yml`
- Create: `.github/workflows/build-android-apk.yml`
- Create: `tests/test_workflows.py`
- Create: `docs/self-hosted-runner.md`

**Interfaces:**
- Consumes: Tasks 1-4 scripts.
- Produces: fast CI on pushes/PRs; manually triggerable APK build with `runner` choice `ubuntu-24.04` or `self-hosted`, defaulting to `ubuntu-24.04`.

- [ ] **Step 1: Write workflow structure tests**

Create `tests/test_workflows.py` that loads workflow files as text and asserts:

- `verify.yml` contains `python3 -m unittest discover -s tests -v`;
- build workflow contains `workflow_dispatch`, a `runner` choice with both `ubuntu-24.04` and `self-hosted`, `./scripts/bootstrap.sh`, `./scripts/verify-patches.sh`, `./scripts/apply-patches.sh`, `./scripts/build-android.sh`, `./scripts/collect-artifacts.sh`, and `actions/upload-artifact@v4`;
- build workflow does not contain `pull_request_target`, unpinned `curl | sh`, or a release signing secret.

- [ ] **Step 2: Run the test and verify failure**

```bash
python3 -m unittest tests.test_workflows -v
```

Expected: failure because workflows do not exist.

- [ ] **Step 3: Add the fast verification workflow**

Create `.github/workflows/verify.yml` using `ubuntu-24.04`, `actions/checkout@v4`, Python 3, and these commands:

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/*.sh scripts/lib/*.sh
```

If `shellcheck` is preinstalled, run it; otherwise install the Ubuntu `shellcheck` package explicitly in the job before running:

```bash
shellcheck scripts/*.sh scripts/lib/*.sh
```

- [ ] **Step 4: Add a manual APK workflow**

Create `.github/workflows/build-android-apk.yml` with `workflow_dispatch` inputs:

```yaml
runner:
  description: Runner label
  required: true
  default: ubuntu-24.04
  type: choice
  options:
    - ubuntu-24.04
    - self-hosted
build_mode:
  description: Build baseline or extension-enabled APK
  required: true
  default: extensions
  type: choice
  options:
    - baseline
    - extensions
```

Set:

```yaml
runs-on: ${{ inputs.runner }}
```

Use `actions/setup-node@v4` with `node-version: '24.16.0'`, run `corepack enable`, use `${{ runner.temp }}/brave-ext-work` as work root, call bootstrap → verify patches → apply patches → build selected mode → collect artifacts, then upload the entire `artifacts/` directory with `actions/upload-artifact@v4`.

Do not enable cache of the Chromium source tree in the first workflow. Correctness and deterministic pins come before optimization.

- [ ] **Step 5: Document runner requirements**

Create `docs/self-hosted-runner.md` describing:

- Linux x86_64 host;
- Node is provisioned by Actions but Brave's native build dependencies must be installable;
- Chromium checkout requires tens of gigabytes; reserve at least 150 GB free disk for source + outputs + intermediate files;
- recommend at least 32 GB RAM, with more preferred for Chromium builds;
- Android SDK/emulator requirements are added in Task 9 for runtime tests;
- no release signing material is required for M0-M1.

State that the GitHub-hosted option is best-effort and can fail for resource limits; switching the workflow input to `self-hosted` is the supported escape path.

- [ ] **Step 6: Run local workflow contract tests**

```bash
python3 -m unittest tests.test_workflows -v
python3 -m unittest discover -s tests -v
```

Expected: pass.

- [ ] **Step 7: Trigger the baseline workflow once**

From GitHub Actions, run `Build Android APK` with:

```text
runner=ubuntu-24.04
build_mode=baseline
```

If it fails specifically due to disk/RAM/job limits, rerun with `runner=self-hosted` after registering the documented runner. Do not change source behavior merely to fit a hosted runner.

Expected successful-run artifact: a ZIP from `actions/upload-artifact` containing `apk/*.apk` and `build-metadata.txt`.

- [ ] **Step 8: Commit**

```bash
git add .github/workflows docs/self-hosted-runner.md tests/test_workflows.py

git commit -m "ci: build Brave Android APK in GitHub Actions"
```

At this point M0 is complete.

---

### Task 6: Prove that upstream extension GN wiring is active without production patches

**Files:**
- Create: `scripts/verify-extension-build.sh`
- Modify: `tests/test_build_plan.py`

**Interfaces:**
- Consumes: generated build directory from extension `--prepare_only`/build.
- Produces: `scripts/verify-extension-build.sh <work-root>`; exits non-zero unless generated GN state reports `enable_desktop_android_extensions = true`, `enable_extensions_core = true`, and `is_desktop_android = false`.

- [ ] **Step 1: Add a verification-script test using a fake GN executable**

Extend `tests/test_build_plan.py` with a temporary fake work tree containing executable `src/buildtools/linux64/gn`. The fake program returns controlled output for:

```text
gn args <out-dir> --list=enable_desktop_android_extensions
gn args <out-dir> --list=enable_extensions_core
gn args <out-dir> --list=is_desktop_android
```

Assert `verify-extension-build.sh` succeeds only for values `true`, `true`, `false` respectively and fails when `enable_extensions_core` returns false.

- [ ] **Step 2: Run the new test and verify failure**

```bash
python3 -m unittest tests.test_build_plan -v
```

Expected: failure because `scripts/verify-extension-build.sh` does not exist.

- [ ] **Step 3: Implement generated-GN verification**

Create `scripts/verify-extension-build.sh` that resolves:

```bash
GN="${WORK_ROOT}/src/buildtools/linux64/gn"
OUT="${WORK_ROOT}/src/out/${BUILD_DIR}"
```

and runs:

```bash
"$GN" args "$OUT" --list=enable_desktop_android_extensions
"$GN" args "$OUT" --list=enable_extensions_core
"$GN" args "$OUT" --list=is_desktop_android
```

Capture each output and require the expected `Current value`/assignment to represent true, true, false. Print all three captured values before returning so CI logs prove the generated configuration.

- [ ] **Step 4: Generate extension build files without compiling everything**

Run:

```bash
cd "$HOME/brave-ext-work/src/brave"
export JAVA_OPTS="-Xmx10G -Xms1G"
pnpm run build Debug \
  -C BraveExtDebug \
  --target_os=android \
  --target_arch=arm64 \
  --target_android_output_format=apk \
  --skip_signing \
  --use_remoteexec=false \
  --gn enable_desktop_android_extensions:true \
  --gn is_desktop_android:false \
  --prepare_only
```

Then:

```bash
./scripts/verify-extension-build.sh "$HOME/brave-ext-work"
```

Expected: the script reports extension Android=true, extension core=true, desktop Android=false.

- [ ] **Step 5: Compile the extension-enabled APK before adding any production source patch**

```bash
./scripts/build-android.sh "$HOME/brave-ext-work" extensions
./scripts/verify-extension-build.sh "$HOME/brave-ext-work"
```

Expected: build links successfully and produces an APK. If it fails, capture the first actual compile/link/runtime error and invoke the `superpowers:systematic-debugging` workflow before creating any production patch. The fix must be the smallest patch that addresses that demonstrated failure.

- [ ] **Step 6: Run unit/syntax tests and commit**

```bash
chmod +x scripts/verify-extension-build.sh
python3 -m unittest tests.test_build_plan -v
bash -n scripts/verify-extension-build.sh

git add scripts/verify-extension-build.sh tests/test_build_plan.py

git commit -m "build: verify Chromium extension core on Android"
```

---

### Task 7: Add a deterministic Manifest V3 fixture

**Files:**
- Create: `fixtures/test-extension/manifest.json`
- Create: `fixtures/test-extension/background.js`
- Create: `fixtures/test-extension/content_script.js`
- Create: `fixtures/test-extension/popup.html`
- Create: `fixtures/test-extension/popup.js`
- Create: `tests/test_fixture.py`

**Interfaces:**
- Consumes: Chromium Manifest V3 runtime.
- Produces: extension named `Brave Android Extensions MVP Fixture`, version `0.1.0`; page marker id `brave-android-extension-fixture`; runtime request `fixture-ping`; runtime reply `fixture-pong`; storage key `fixtureSeen`.

- [ ] **Step 1: Write the fixture contract test**

Create `tests/test_fixture.py`:

```python
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "test-extension"


class ExtensionFixtureTest(unittest.TestCase):
    def test_manifest_and_sources_are_deterministic(self) -> None:
        manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["name"], "Brave Android Extensions MVP Fixture")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["permissions"], ["storage"])
        self.assertEqual(manifest["background"]["service_worker"], "background.js")
        self.assertEqual(manifest["action"]["default_popup"], "popup.html")
        self.assertEqual(manifest["content_scripts"][0]["matches"], ["http://match.test/*"])

        content = (FIXTURE / "content_script.js").read_text(encoding="utf-8")
        background = (FIXTURE / "background.js").read_text(encoding="utf-8")
        self.assertIn("brave-android-extension-fixture", content)
        self.assertIn("fixture-content-script-ok", content)
        self.assertIn("fixture-ping", background)
        self.assertIn("fixture-pong", background)
        self.assertIn("fixtureSeen", background)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and verify failure**

```bash
python3 -m unittest tests.test_fixture -v
```

Expected: failure because fixture files do not exist.

- [ ] **Step 3: Create the manifest**

`fixtures/test-extension/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "Brave Android Extensions MVP Fixture",
  "version": "0.1.0",
  "permissions": ["storage"],
  "host_permissions": ["http://match.test/*"],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html"
  },
  "content_scripts": [
    {
      "matches": ["http://match.test/*"],
      "js": ["content_script.js"],
      "run_at": "document_idle"
    }
  ]
}
```

- [ ] **Step 4: Create content/background code**

`fixtures/test-extension/content_script.js`:

```javascript
const marker = document.createElement('div')
marker.id = 'brave-android-extension-fixture'
marker.textContent = 'fixture-content-script-ok'
document.documentElement.appendChild(marker)
```

`fixtures/test-extension/background.js`:

```javascript
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message !== 'fixture-ping') {
    return false
  }

  chrome.storage.local.set({ fixtureSeen: true }).then(() => {
    sendResponse({ reply: 'fixture-pong' })
  })
  return true
})
```

- [ ] **Step 5: Create the action popup fixture**

`fixtures/test-extension/popup.html`:

```html
<!doctype html>
<html>
  <body>
    <output id="state">unknown</output>
    <script src="popup.js"></script>
  </body>
</html>
```

`fixtures/test-extension/popup.js`:

```javascript
chrome.storage.local.get('fixtureSeen').then(({ fixtureSeen }) => {
  document.getElementById('state').textContent = fixtureSeen ? 'seen' : 'not-seen'
})
```

- [ ] **Step 6: Run the fixture tests and commit**

```bash
python3 -m unittest tests.test_fixture -v

git add fixtures tests/test_fixture.py

git commit -m "test: add Android MV3 extension fixture"
```

---

### Task 8: Stage the fixture and add one Chromium Android browser test

**Files:**
- Create: `scripts/stage-test-fixture.sh`
- Create: `patches/0001-brave-android-extension-fixture-test.patch`
- Modify: `tests/test_patch_scripts.py`

**Interfaces:**
- Consumes: project fixture from Task 7 and Chromium 153 source tree.
- Produces: staged test data at `chrome/test/data/extensions/brave_android_mvp`; Chromium test `DesktopAndroidExtensionsBrowserTest.BraveMvpFixtureContentScript`.

- [ ] **Step 1: Add a staging test**

Extend `tests/test_patch_scripts.py` to create a temporary fake Chromium root with `chrome/test/data/extensions/`, run:

```bash
scripts/stage-test-fixture.sh <fake-src-root>
```

and assert the staged directory contains byte-for-byte copies of all five fixture files.

- [ ] **Step 2: Implement fixture staging**

Create `scripts/stage-test-fixture.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
if [[ $# -ne 1 ]]; then
  printf 'Usage: %s <chromium-src-root>\n' "$0" >&2
  exit 2
fi
SRC_ROOT="$(cd "$1" && pwd)"
SOURCE="${PROJECT_ROOT}/fixtures/test-extension"
DEST="${SRC_ROOT}/chrome/test/data/extensions/brave_android_mvp"

rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "${SOURCE}/." "$DEST/"
```

- [ ] **Step 3: Generate a narrow test-only patch against Chromium 153.0.8010.18**

Start from the pinned work tree after a clean bootstrap. Edit only:

```text
chrome/browser/extensions/desktop_android/desktop_android_extensions_browsertest.cc
```

Add a test that loads the staged unpacked fixture using the existing `ChromeTestExtensionLoader`, navigates to `http://match.test/title1.html`, and asserts:

```javascript
document.getElementById('brave-android-extension-fixture').textContent
```

returns exactly:

```text
fixture-content-script-ok
```

Use the same fixture/embedded-server patterns already present in `DesktopAndroidExtensionsBrowserTest.ContentScriptInjection`; do not add a second extension loader implementation.

The new C++ test name must be exactly:

```cpp
IN_PROC_BROWSER_TEST_F(DesktopAndroidExtensionsBrowserTest,
                       BraveMvpFixtureContentScript)
```

Generate a root-relative unified diff from the Chromium `src/` root and save it as `patches/0001-brave-android-extension-fixture-test.patch`. The patch must contain only the single browser-test source file; fixture files remain owned by this overlay and are staged by script.

- [ ] **Step 4: Verify the patch applies cleanly**

From the overlay repository:

```bash
./scripts/verify-patches.sh "$HOME/brave-ext-work/src"
```

Expected: `0001-brave-android-extension-fixture-test.patch` passes dry-run with zero rejects/fuzz errors.

- [ ] **Step 5: Test actual apply + stage on a disposable clean checkout**

```bash
./scripts/apply-patches.sh "$HOME/brave-ext-work/src"
./scripts/stage-test-fixture.sh "$HOME/brave-ext-work/src"
test -f "$HOME/brave-ext-work/src/chrome/test/data/extensions/brave_android_mvp/manifest.json"
```

Expected: success.

- [ ] **Step 6: Run overlay tests/syntax checks and commit**

```bash
chmod +x scripts/stage-test-fixture.sh
python3 -m unittest tests.test_patch_scripts tests.test_fixture -v
bash -n scripts/stage-test-fixture.sh

git add scripts/stage-test-fixture.sh patches/0001-brave-android-extension-fixture-test.patch tests/test_patch_scripts.py

git commit -m "test: wire MV3 fixture into Chromium Android browser tests"
```

---

### Task 9: Execute focused extension runtime tests on Android x86

**Files:**
- Create: `scripts/test-extension-runtime.sh`
- Create: `tests/test_runtime_test_plan.py`
- Modify: `docs/self-hosted-runner.md`
- Create: `docs/compatibility.md`

**Interfaces:**
- Consumes: initialized/patched/staged source and Android x86 emulator.
- Produces: `scripts/test-extension-runtime.sh [--print-plan] <work-root>`; focused test filter proving upstream extension system + project fixture.

- [ ] **Step 1: Write the runtime command-plan test**

Create `tests/test_runtime_test_plan.py` and assert `--print-plan` output contains:

```text
pnpm run test brave_browser_tests
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

- [ ] **Step 2: Run it and verify failure**

```bash
python3 -m unittest tests.test_runtime_test_plan -v
```

Expected: failure because runtime script does not exist.

- [ ] **Step 3: Implement the focused runtime test command**

Create `scripts/test-extension-runtime.sh` with `--print-plan` support. Before invoking Brave tests, run:

```bash
"${SCRIPT_DIR}/stage-test-fixture.sh" "${WORK_ROOT}/src"
```

Build the colon-separated filter:

```text
DesktopAndroidExtensionsBrowserTest.BraveMvpFixtureContentScript:DesktopAndroidExtensionsBrowserTest.ServiceWorkerBasedExtension:DesktopAndroidExtensionsBrowserTest.ContentScriptInjection:DesktopAndroidExtensionsBrowserTest.StorageApiTestStorageAreaLocal:DesktopAndroidExtensionsBrowserTest.MessagePassing
```

Then execute from `<work-root>/src/brave`:

```bash
pnpm run test brave_browser_tests \
  --target_os=android \
  --target_arch=x86 \
  --manual_android_test_device \
  --gn enable_desktop_android_extensions:true \
  --gn is_desktop_android:false \
  --filter="$FILTER"
```

Use `JAVA_OPTS="${JAVA_OPTS:--Xmx10G -Xms1G}"` consistently with the build script.

- [ ] **Step 4: Document emulator prerequisites**

Extend `docs/self-hosted-runner.md` with the runtime-test machine contract:

- Android SDK + adb available on PATH;
- x86 Android emulator image installed;
- emulator already booted before `runtime-extension-tests.yml` starts;
- `adb devices` must show exactly one usable target for the initial setup;
- runner account can execute adb/emulator without interactive prompts.

Include preflight commands:

```bash
adb devices
adb shell getprop sys.boot_completed
```

Expected second command: `1`.

- [ ] **Step 5: Run the focused browser tests on the emulator**

On the self-hosted test runner/workstation:

```bash
./scripts/test-extension-runtime.sh "$HOME/brave-ext-work"
```

Expected: all five filtered tests pass. This is the M1 runtime gate. If a test target/name has changed in the pinned Chromium revision, inspect the exact generated target/test list and update the script/test contract in the same commit; do not silently skip a capability test.

- [ ] **Step 6: Record only proven compatibility**

Create `docs/compatibility.md` with an M1 table:

```markdown
| Capability | M1 status | Evidence |
| --- | --- | --- |
| Manifest V3 unpacked load | Proven | DesktopAndroidExtensionsBrowserTest + project fixture |
| Content scripts | Proven | BraveMvpFixtureContentScript + ContentScriptInjection |
| MV3 service worker | Proven | ServiceWorkerBasedExtension |
| storage.local | Proven | StorageApiTestStorageAreaLocal |
| runtime messaging | Proven | MessagePassing |
| General CRX install | Not implemented in M1 | Planned for M2 |
| Mobile extension manager | Not implemented in M1 | Planned for M2 |
| Action popup UI | Not implemented in M1 | Planned for M3 |
| Chrome Web Store | Not implemented in M1 | Planned for M4 |
```

Do not claim compatibility for third-party extensions based only on these fixture tests.

- [ ] **Step 7: Run local tests and commit**

```bash
chmod +x scripts/test-extension-runtime.sh
python3 -m unittest tests.test_runtime_test_plan tests.test_fixture -v
bash -n scripts/test-extension-runtime.sh

git add scripts/test-extension-runtime.sh tests/test_runtime_test_plan.py docs/self-hosted-runner.md docs/compatibility.md

git commit -m "test: verify Android Chromium extension runtime"
```

---

### Task 10: Put the M1 runtime gate and extension APK into CI

**Files:**
- Create: `.github/workflows/runtime-extension-tests.yml`
- Modify: `.github/workflows/build-android-apk.yml`
- Modify: `tests/test_workflows.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: manual self-hosted M1 test workflow; extension-enabled APK becomes the documented primary development artifact after the M1 gate passes.

- [ ] **Step 1: Extend workflow tests before adding the runtime workflow**

Update `tests/test_workflows.py` to assert `runtime-extension-tests.yml`:

- is `workflow_dispatch` only;
- uses `runs-on: self-hosted`;
- calls bootstrap, verify/apply patches, stage fixture, and `test-extension-runtime.sh`;
- does not use release secrets or third-party setup actions.

Also assert the APK workflow default `build_mode` is `extensions`.

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_workflows -v
```

Expected: failure because the runtime workflow is absent and APK default may still be baseline.

- [ ] **Step 3: Add the self-hosted runtime workflow**

Create `.github/workflows/runtime-extension-tests.yml`:

- `workflow_dispatch` trigger;
- `runs-on: self-hosted`;
- checkout overlay;
- setup Node `24.16.0` using `actions/setup-node@v4`;
- `corepack enable`;
- `adb devices` and boot-complete preflight;
- bootstrap into `${{ runner.temp }}/brave-ext-work`;
- verify/apply patches;
- run `scripts/test-extension-runtime.sh`.

Do not make the workflow start an emulator in this first version; runner/emulator provisioning belongs to the self-hosted machine contract and avoids hiding an expensive virtualization dependency inside project code.

- [ ] **Step 4: Promote extension build mode as the default development APK**

Change `.github/workflows/build-android-apk.yml` input default:

```yaml
build_mode:
  default: extensions
```

Keep `baseline` as a selectable diagnostic control.

After the build command, call:

```bash
./scripts/verify-extension-build.sh "${WORK_ROOT}"
```

only when `build_mode=extensions`.

- [ ] **Step 5: Update README with exact M0/M1 commands**

Document:

```bash
python3 -m unittest discover -s tests -v
./scripts/bootstrap.sh "$HOME/brave-ext-work"
./scripts/verify-patches.sh "$HOME/brave-ext-work/src"
./scripts/apply-patches.sh "$HOME/brave-ext-work/src"
./scripts/build-android.sh "$HOME/brave-ext-work" extensions
./scripts/verify-extension-build.sh "$HOME/brave-ext-work"
./scripts/test-extension-runtime.sh "$HOME/brave-ext-work"
```

State clearly:

- APK is an unofficial development build;
- M1 proves extension runtime capabilities, not Chrome Web Store/general CRX installation;
- M2 starts only after runtime workflow and extension APK workflow both pass.

- [ ] **Step 6: Run complete overlay verification**

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/*.sh scripts/lib/*.sh
shellcheck scripts/*.sh scripts/lib/*.sh
```

Expected: all pass.

- [ ] **Step 7: Run the two GitHub Actions gates**

Trigger `Build Android APK` with:

```text
build_mode=extensions
runner=self-hosted
```

Expected: downloadable artifact containing at least one APK and build metadata.

Then trigger `Runtime Extension Tests` on a self-hosted runner with the x86 emulator already booted.

Expected: all five focused extension tests pass.

- [ ] **Step 8: Record final M1 evidence**

Add to `docs/compatibility.md` the GitHub Actions run identifiers/commit SHA that produced the successful extension APK and runtime test result. Use immutable commit SHA/run IDs, not screenshots, as the evidence references.

- [ ] **Step 9: Commit**

```bash
git add .github/workflows README.md tests/test_workflows.py docs/compatibility.md

git commit -m "ci: gate Brave Android extension runtime"
```

---

## M0-M1 completion gate

Do not begin the M2 manager/CRX implementation until all of the following are true on the same overlay commit:

```text
[ ] python3 -m unittest discover -s tests -v passes
[ ] shell syntax + shellcheck pass
[ ] pinned Brave Core revision verifies as 1.96.43 / Chromium 153.0.8010.18
[ ] baseline ARM64 Brave debug APK builds
[ ] extension-enabled ARM64 APK builds with:
    enable_desktop_android_extensions=true
    enable_extensions_core=true
    is_desktop_android=false
[ ] extension APK is uploaded as a GitHub Actions artifact
[ ] BraveMvpFixtureContentScript passes on Android x86
[ ] upstream MV3 service-worker test passes on Android x86
[ ] upstream content-script test passes on Android x86
[ ] upstream storage.local test passes on Android x86
[ ] upstream runtime-message test passes on Android x86
[ ] docs/compatibility.md claims only capabilities demonstrated by those tests
```

When this gate is green, write a separate M2 design/implementation plan for the native mobile Extensions manager and validated local CRX installation. M3, M4, and M5 remain separate reviewable projects.
