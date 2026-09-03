# Brave Android Extensions — design

Date: 2026-09-03
Repository: `tkinder221-del/moja-pierwsza-strona`
Status: approved architecture, pre-implementation

## Goal

Build a maintainable Android browser derived from current Brave/Chromium that preserves Brave's Android browser features while adding a user-facing Chromium extension system. The project should produce installable Android APK artifacts from GitHub Actions and minimize long-lived divergence from upstream Chromium.

The first usable milestone is an MVP, not full desktop-extension parity.

## Primary success criteria

1. A GitHub Actions workflow can fetch a pinned Brave source revision and its matching Chromium source, apply this repository's patch set, and build an Android APK.
2. The resulting browser launches as a Brave-derived Android application.
3. Chromium extension core is enabled for Android using current upstream Android-extension infrastructure wherever possible, rather than reviving Brave's old 2020 patch set.
4. The browser exposes a mobile Extensions manager reachable from the application menu.
5. The manager can list installed extensions, enable/disable them, remove them, and show basic metadata/permissions.
6. An extension can be installed from a local CRX package. ZIP/unpacked development installation is optional within MVP if it can be implemented without destabilizing CRX installation.
7. Extension content scripts/background/service-worker functionality is tested with a small compatibility fixture extension.
8. Build output is uploaded as a GitHub Actions artifact.

## Architecture decision

This repository is an overlay/patch-set and build-orchestration project, not a permanent copy of the complete Brave/Chromium source tree.

At build time:

1. Resolve a pinned Brave revision from `config/brave-version.env`.
2. Fetch/initialize Brave using Brave's supported source bootstrap process.
3. Let Brave resolve its matching Chromium revision.
4. Apply patches from this repository in deterministic numeric order.
5. Apply Android build arguments from this repository.
6. Build an APK.
7. Run smoke/static checks.
8. Upload the APK and build metadata as Actions artifacts.

This keeps the maintained delta reviewable and makes Chromium/Brave upgrades explicit: update the pin, attempt patch application/build, then repair only the patches that conflict.

## Repository layout

```text
.
├── README.md
├── config/
│   ├── brave-version.env
│   └── android-extension-args.gn
├── patches/
│   ├── 0001-enable-extension-core-on-android.patch
│   ├── 0002-android-extension-runtime-wiring.patch
│   ├── 0003-mobile-extensions-manager.patch
│   ├── 0004-local-crx-installer.patch
│   └── 0005-extension-menu-integration.patch
├── fixtures/
│   └── test-extension/
├── scripts/
│   ├── bootstrap.sh
│   ├── apply-patches.sh
│   ├── build-android.sh
│   ├── verify-patches.sh
│   └── collect-artifacts.sh
├── .github/workflows/
│   ├── verify.yml
│   └── build-android-apk.yml
└── docs/
    ├── compatibility.md
    └── superpowers/specs/
```

Patch filenames are conceptual boundaries. If upstream Chromium already implements part of a boundary, the corresponding patch should shrink or disappear rather than duplicating upstream code.

## Upstream strategy

Prefer current Chromium Android extension infrastructure, including `enable_desktop_android_extensions` / extension-core build pathways, over Brave's historical Android-extension proof of concept.

Rules:

- Use upstream classes and build flags whenever they are functional on standard mobile Android.
- Avoid broad `IS_ANDROID` removals unless the underlying subsystem has been audited for Android.
- Keep Brave-specific changes in `brave/chromium_src`, Android Java/Kotlin UI, or narrowly scoped build configuration where practical.
- Do not import the old Brave proof-of-concept wholesale; it touched hundreds of files and is unsuitable as the maintenance base.
- Cromite/other open-source Android Chromium browsers may be implementation references, but code is copied only when licensing is compatible and the change remains necessary against the pinned current Chromium revision.

## Runtime components

### 1. Extension-core enablement

Enable the Chromium extension subsystem for the Android target using current build flags. Compile-time success is not sufficient: initialization paths must create the extension system/profile services required by loaded extensions.

### 2. Android extension browser client wiring

Audit and provide Android implementations or safe fallbacks for extension services that desktop Chromium assumes exist. Unsupported desktop-only APIs must fail cleanly rather than crash.

The MVP compatibility target prioritizes:

- Manifest V3 extension loading
- content scripts
- `storage`
- `runtime` messaging
- basic `tabs` access where Android provides an equivalent
- service-worker/background execution
- host permissions
- `action` metadata and popup launching where feasible

Not required for MVP:

- DevTools extension panels
- native messaging
- desktop side-panel APIs
- arbitrary desktop window-management semantics
- perfect keyboard shortcut parity

### 3. Mobile Extensions manager

Add a native Android screen reachable from the main Brave menu as `Extensions` / `Rozszerzenia`.

Initial screen behavior:

- list extension name, icon, version and enabled state
- open details
- enable/disable
- uninstall
- install from file
- show an explicit warning when an extension requires unsupported APIs

The manager should call the Chromium extension service through a narrow Android bridge rather than implementing a second extension database in Java/Kotlin.

### 4. Extension actions/popups

Expose installed extension actions through an `Extensions` menu. The MVP does not require a permanent desktop-style puzzle icon in the toolbar if that creates excessive Android UI churn; the menu is the stable first surface.

For extensions with `action.default_popup`, open the extension URL in a constrained browser-owned surface. If popup hosting proves blocked by upstream Android assumptions, the fallback for MVP is opening the extension page in a dedicated tab while retaining extension origin/context.

### 5. Local installation

MVP installation source: a local `.crx` selected through Android's Storage Access Framework.

Install flow:

1. User selects a CRX.
2. Native code reads it from a content URI into controlled temporary storage.
3. Chromium's CRX validation/unpacking path validates package structure/signature.
4. The app displays extension identity, requested host/API permissions, package source and risk warning.
5. User explicitly confirms.
6. The extension service installs it into the current browser profile.
7. Temporary package data is removed.

Do not silently install arbitrary downloads.

ZIP/unpacked installation is a developer-mode follow-up. If included in MVP, it must be visibly labelled Developer mode and not share the normal trusted-install UX.

### 6. Chrome Web Store

Chrome Web Store installation is milestone M4, after the runtime, local CRX management and extension-action UX have been proven stable.

The intended UX is to recognize Chrome Web Store extension pages and offer an install action. Implementation must use a supportable package/update path; it must not depend on scraping fragile page HTML. If Google's current store/install endpoints cannot be used reliably by a non-Chrome Android client, Web Store pages may initially guide the user to obtain a CRX instead.

Third-party CRX sites such as crxsoso.com are treated only as external package sources. The browser must not imply that packages from them are trusted or equivalent to Chrome Web Store packages.

## Security model

Extensions execute privileged code relative to normal websites, so the feature is explicitly user-controlled.

Requirements:

- no background installation without user confirmation
- verify CRX package integrity/signature using Chromium's implementation
- display requested permissions before final install
- clearly identify sideloaded extensions
- preserve Chromium extension process/site isolation decisions
- no custom bypass for unsafe-extension warnings merely to improve compatibility
- unsupported APIs return errors/no-op behavior rather than exposing partially initialized native services
- normal and incognito/private-profile extension policies remain separate

The project will not implement mechanisms to bypass Android, Chrome Web Store or enterprise security controls.

## Build and CI

### Verification workflow

`verify.yml` runs on pull requests and relevant pushes:

- shell formatting/lint checks
- patch ordering and clean-apply validation against the pinned source revision where resource limits permit
- fixture manifest validation
- optional targeted source/unit tests once patches exist

### APK workflow

`build-android-apk.yml` is manually triggerable first. After the pipeline is stable, pushes to a release branch/tag may trigger it automatically.

Steps:

1. checkout overlay repository
2. install host prerequisites and Brave-supported Node/pnpm tooling
3. cache only safe/reusable dependency layers
4. fetch Brave source at the pinned revision
5. run Brave sync for Android
6. apply overlay patches
7. generate Android output args
8. build debug APK using Brave's Android target with APK output format
9. record Brave commit, Chromium revision and overlay commit
10. upload APK + metadata + patch log

A Chromium/Brave build is large. GitHub-hosted runners may be unable to complete it reliably due to disk, RAM or job-duration limits. The workflow therefore supports a `self-hosted` runner mode as the production path. GitHub-hosted runner support is best-effort and is not a success criterion if upstream build resource requirements exceed hosted-runner limits.

No release signing key is stored in the repository. MVP artifacts are debug/development APKs. Release signing is a separate milestone using GitHub Actions secrets or an external signing process.

## Testing strategy

### Patch/build tests

- every patch applies without fuzz/rejects to the pinned revision
- GN generation completes with extension flags enabled
- Android target links successfully

### Runtime fixture

Create a small MV3 fixture extension containing:

- content script adding a deterministic marker to a test page
- service worker
- `storage.local` read/write
- runtime message round-trip
- action/popup page

This provides a known-good extension that does not depend on Chrome Web Store behavior.

### Android tests

As implementation permits:

- manager lists fixture extension
- enable/disable changes runtime behavior
- uninstall removes runtime behavior
- CRX install rejects corrupt package
- CRX install requires confirmation
- valid fixture CRX installs and executes content script
- browser starts normally when no extensions are installed

Manual compatibility testing may additionally cover representative third-party MV3 extensions. Third-party compatibility is not guaranteed by MVP.

## Error handling

- Patch mismatch: fail CI immediately and identify the first failing patch.
- Missing upstream feature/API: fail build or mark the API unsupported; never paper over it with unsafe casts/stubs that can crash at runtime.
- Invalid CRX: reject before permission confirmation/install.
- Unsupported manifest/API: show a user-readable incompatibility message when it can be detected at install time.
- Build runner resource exhaustion: preserve logs and document self-hosted runner requirements.

## Milestones

### M0 — Build skeleton

Overlay repository structure, pinned Brave revision, bootstrap/apply/build scripts, GitHub Actions workflow, unchanged Brave debug APK build.

### M1 — Extension runtime MVP

Enable extension core, initialize required services and prove the bundled fixture extension executes on Android.

### M2 — User management + CRX

Native Extensions manager, enable/disable/uninstall, file picker, validated CRX install with permission confirmation.

### M3 — Actions/popups

Extensions menu and extension action/popup UX.

### M4 — Chrome Web Store integration

Install flow from Chrome Web Store where technically/supportably possible, plus update behavior and clear provenance UI.

### M5 — Compatibility hardening

Test common MV3 extensions, document unsupported APIs, fix high-value Android gaps while keeping the patch delta small.

## Non-goals for the first implementation cycle

- publishing to Google Play
- pretending to be official Brave
- release signing/automatic production updates
- full Manifest V2 resurrection if current Chromium removed required runtime support
- supporting every desktop Chrome extension API
- bypassing paid/protected extension distribution
- automatic trust of third-party CRX mirrors

## Branding and distribution

Development builds must use distinct application branding/package identity before public distribution to avoid confusion with official Brave. During the earliest compile/runtime spike, upstream Brave branding may remain temporarily if necessary to prove the build, but public artifacts/releases must be clearly identified as an unofficial fork.

## Definition of the first deliverable

The first deliverable is complete when a GitHub Actions or documented self-hosted Actions run produces an installable development APK from a pinned Brave revision and the same source tree can load and execute the project's deterministic MV3 fixture extension. The mobile manager and general CRX sideloading then build on that verified runtime rather than being developed against an unproven extension subsystem.
