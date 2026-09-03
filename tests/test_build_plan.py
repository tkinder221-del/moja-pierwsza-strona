from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildPlanTest(unittest.TestCase):
    def run_plan(self, mode: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "src" / "brave").mkdir(parents=True)
            result = subprocess.run(
                [str(ROOT / "scripts" / "build-android.sh"), "--print-plan", str(work), mode],
                check=True,
                text=True,
                capture_output=True,
            )
            return result.stdout

    def test_baseline_plan(self) -> None:
        out = self.run_plan("baseline")
        self.assertIn("pnpm run build Debug", out)
        self.assertIn("-C BraveExtDebug", out)
        self.assertIn("--target_os=android", out)
        self.assertIn("--target_arch=arm64", out)
        self.assertIn("--target_android_output_format=apk", out)
        self.assertIn("--skip_signing", out)
        self.assertIn("--use_remoteexec=false", out)
        self.assertNotIn("enable_desktop_android_extensions:true", out)

    def test_extension_plan_adds_gn_args(self) -> None:
        out = self.run_plan("extensions")
        self.assertIn("--gn enable_desktop_android_extensions:true", out)
        self.assertIn("--gn is_desktop_android:false", out)

    def test_collect_artifacts_copies_unknown_apk_name_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            out = root / "artifacts"
            apk_dir = work / "src" / "out" / "BraveExtDebug" / "apks"
            apk_dir.mkdir(parents=True)
            (apk_dir / "fixture.apk").write_bytes(b"apk")
            subprocess.run(
                [str(ROOT / "scripts" / "collect-artifacts.sh"), str(work), str(out)],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertEqual((out / "apk" / "fixture.apk").read_bytes(), b"apk")
            metadata = (out / "build-metadata.txt").read_text(encoding="utf-8")
            self.assertIn("BRAVE_CORE_REF=f437ba81810858a15a961f13aab4fa24bb3ccce2", metadata)
            self.assertIn("BRAVE_VERSION=1.96.43", metadata)
            self.assertIn("CHROMIUM_VERSION=153.0.8010.18", metadata)
            self.assertIn("APK_TARGET_ARCH=arm64", metadata)
            self.assertIn("BUILD_DIR=BraveExtDebug", metadata)
            self.assertIn("OVERLAY_COMMIT=", metadata)


if __name__ == "__main__":
    unittest.main()
