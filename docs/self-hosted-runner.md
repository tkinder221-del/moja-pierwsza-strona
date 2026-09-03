# Self-hosted runner requirements

The Brave/Chromium Android build is resource-intensive. For reliable M0-M1 builds, use a Linux x86_64 GitHub Actions self-hosted runner with at least 150 GB of free disk space. At least 32 GB RAM is recommended.

The runner must provide Git, Python 3, standard Linux build tooling and permission to install Brave/Chromium Android build prerequisites. Node 24.16.0 is configured by the workflow; pnpm is provided through Corepack/Brave's package-manager constraints.

GitHub-hosted `ubuntu-24.04` is supported as a best-effort option, but may fail because of disk, memory, or job-duration limits. A failure caused only by those resource limits should be retried on the self-hosted runner without changing product code.

No release signing material is required for M0-M1. These workflows produce development/debug APK artifacts and must not store Android release keystores or private signing keys in the repository.

## Android emulator preflight for M1

Runtime extension tests require the Android SDK and `adb` on `PATH`, an x86 Android emulator image installed, and a booted emulator before the GitHub Actions job starts. For the initial M1 gate, expose exactly one usable adb target to avoid ambiguous device selection.

Run:

```bash
adb devices
adb shell getprop sys.boot_completed
```

The boot-completed property must return `1` before starting the runtime workflow.
