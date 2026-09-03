# Brave Android Extensions Overlay

Unofficial development overlay for building a Brave-derived Android browser with Chromium's experimental Android extension runtime enabled.

This repository does not contain the full Brave/Chromium source tree. It pins Brave Core, bootstraps the matching Chromium revision, applies a small reviewed patch set, and provides repeatable build/test scripts.

Current scope is M0-M1: reproducible Android debug APK builds and focused Android extension-runtime tests. M1 proves the runtime only; arbitrary CRX installation, a mobile Extensions manager, action/popup UI, Chrome Web Store integration, release signing, and public distribution are not implemented yet.

Design: `docs/superpowers/specs/2026-09-03-brave-android-extensions-design.md`

Implementation plan: `docs/superpowers/plans/2026-09-03-brave-android-extensions-m0-m1.md`

## Fast local checks

```bash
python3 -m unittest discover -s tests -v
bash ./scripts/bootstrap.sh --print-plan /tmp/brave-ext-work
bash ./scripts/build-android.sh --print-plan /tmp/brave-ext-work extensions
```

## M0-M1 build and runtime flow

On a capable Linux build machine:

```bash
python3 -m unittest discover -s tests -v
bash ./scripts/bootstrap.sh "$HOME/brave-ext-work"
bash ./scripts/verify-patches.sh "$HOME/brave-ext-work/src"
bash ./scripts/apply-patches.sh "$HOME/brave-ext-work/src"
bash ./scripts/build-android.sh "$HOME/brave-ext-work" extensions
bash ./scripts/verify-extension-build.sh "$HOME/brave-ext-work"
bash ./scripts/test-extension-runtime.sh "$HOME/brave-ext-work"
```

The APK workflow can also build `baseline` for diagnostics. The normal development target is `extensions`.
