from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTestPlan(unittest.TestCase):
    def test_print_plan_contains_all_m1_capability_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "src" / "brave").mkdir(parents=True)
            result = subprocess.run(
                [str(ROOT / "scripts" / "test-extension-runtime.sh"), "--print-plan", str(work)],
                check=True,
                text=True,
                capture_output=True,
            )
        out = result.stdout
        self.assertIn("stage-test-fixture.sh", out)
        self.assertIn("pnpm run test browser_tests", out)
        self.assertIn("--target_os=android", out)
        self.assertIn("--target_arch=x86", out)
        self.assertIn("--manual_android_test_device", out)
        self.assertIn("--gn enable_desktop_android_extensions:true", out)
        self.assertIn("--gn is_desktop_android:false", out)
        for name in (
            "DesktopAndroidExtensionsBrowserTest.BraveMvpFixtureContentScript",
            "DesktopAndroidExtensionsBrowserTest.ServiceWorkerBasedExtension",
            "DesktopAndroidExtensionsBrowserTest.ContentScriptInjection",
            "DesktopAndroidExtensionsBrowserTest.StorageApiTestStorageAreaLocal",
            "DesktopAndroidExtensionsBrowserTest.MessagePassing",
        ):
            self.assertIn(name, out)


if __name__ == "__main__":
    unittest.main()
