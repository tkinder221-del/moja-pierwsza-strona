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
