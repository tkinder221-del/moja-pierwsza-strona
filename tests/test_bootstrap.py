from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapPlanTest(unittest.TestCase):
    def test_print_plan_is_pinned_and_uses_brave_supported_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                ["bash", str(ROOT / "scripts" / "bootstrap.sh"), "--print-plan", tmp],
                check=True,
                text=True,
                capture_output=True,
            )
        out = result.stdout
        self.assertIn("src/brave", out)
        self.assertIn("f437ba81810858a15a961f13aab4fa24bb3ccce2", out)
        self.assertIn("expected Brave version: 1.96.43", out)
        self.assertIn("expected Chromium version: 153.0.8010.18", out)
        self.assertIn("pnpm run init --target_os=android --target_arch=arm64", out)
        self.assertIn("install-build-deps.sh --android", out)


if __name__ == "__main__":
    unittest.main()
