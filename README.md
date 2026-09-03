# Brave Android Extensions Overlay

Unofficial development overlay for building a Brave-derived Android browser with Chromium's experimental Android extension runtime enabled.

This repository does not contain the full Brave/Chromium source tree. It pins Brave Core, bootstraps the matching Chromium revision, applies a small reviewed patch set, and provides repeatable build/test scripts.

Current scope: M0-M1 only — reproducible ARM64 debug APK build plus x86 Android-emulator tests for the extension runtime. Mobile extension management, arbitrary CRX installation, popup UX, Chrome Web Store integration, release signing, and public distribution are later milestones.

Design: `docs/superpowers/specs/2026-09-03-brave-android-extensions-design.md`

Implementation plan: `docs/superpowers/plans/2026-09-03-brave-android-extensions-m0-m1.md`

Quick checks:

```bash
python3 -m unittest discover -s tests -v
./scripts/bootstrap.sh --print-plan /tmp/brave-ext-work
./scripts/build-android.sh --print-plan /tmp/brave-ext-work extensions
```
