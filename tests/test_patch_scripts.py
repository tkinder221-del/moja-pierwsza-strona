from pathlib import Path
import difflib
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def make_patch(before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/sample.txt",
            tofile="b/sample.txt",
        )
    )


class PatchScriptsTest(unittest.TestCase):
    def test_patches_apply_in_lexicographic_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            patches = root / "patches"
            src.mkdir()
            patches.mkdir()
            (src / "sample.txt").write_text("start\n", encoding="utf-8")
            (patches / "0001-first.patch").write_text(
                make_patch("start\n", "first\n"), encoding="utf-8"
            )
            (patches / "0002-second.patch").write_text(
                make_patch("first\n", "first\nsecond\n"), encoding="utf-8"
            )
            env = os.environ.copy()
            env["OVERLAY_PATCH_DIR"] = str(patches)
            subprocess.run(
                [str(ROOT / "scripts" / "verify-patches.sh"), str(src)],
                check=True,
                text=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                [str(ROOT / "scripts" / "apply-patches.sh"), str(src)],
                check=True,
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual((src / "sample.txt").read_text(encoding="utf-8"), "first\nsecond\n")

    def test_empty_patch_directory_is_a_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            patches = root / "patches"
            src.mkdir()
            patches.mkdir()
            env = os.environ.copy()
            env["OVERLAY_PATCH_DIR"] = str(patches)
            result = subprocess.run(
                [str(ROOT / "scripts" / "apply-patches.sh"), str(src)],
                check=True,
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(result.stdout.strip(), "No overlay patches to apply.")


if __name__ == "__main__":
    unittest.main()
