# Overlay patch policy

Patch files are named `NNNN-description.patch` and are applied in lexicographic order from the Chromium `src/` root with `patch -p1`.

Every patch is dry-run checked immediately before mutation. A reject or context mismatch stops the process. Production Chromium patches are permitted only after a concrete compile or runtime failure demonstrates that the current upstream Android extension path is insufficient. Test-only patches may be used to add deterministic verification coverage.
