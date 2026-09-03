from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTest(unittest.TestCase):
    def read(self, name: str) -> str:
        return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")

    def test_verify_workflow_runs_overlay_checks(self) -> None:
        text = self.read("verify.yml")
        self.assertIn("ubuntu-24.04", text)
        self.assertIn("actions/checkout@v4", text)
        self.assertIn("python3 -m unittest discover -s tests -v", text)
        self.assertIn("bash -n scripts/*.sh scripts/lib/*.sh", text)
        self.assertIn("shellcheck scripts/*.sh scripts/lib/*.sh", text)

    def test_build_workflow_is_manual_and_safe(self) -> None:
        text = self.read("build-android-apk.yml")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("ubuntu-24.04", text)
        self.assertIn("self-hosted", text)
        self.assertIn("baseline", text)
        self.assertIn("extensions", text)
        self.assertIn("default: extensions", text)
        self.assertIn("actions/checkout@v4", text)
        self.assertIn("actions/setup-node@v4", text)
        self.assertIn("node-version: '24.16.0'", text)
        for command in (
            "./scripts/bootstrap.sh",
            "./scripts/verify-patches.sh",
            "./scripts/apply-patches.sh",
            "./scripts/build-android.sh",
            "./scripts/collect-artifacts.sh",
            "./scripts/verify-extension-build.sh",
        ):
            self.assertIn(command, text)
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertNotIn("pull_request_target", text)
        self.assertNotIn("SIGNING", text.upper())
        self.assertNotIn("curl | sh", text)

    def test_runtime_workflow_gates_android_extension_tests(self) -> None:
        text = self.read("runtime-extension-tests.yml")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("runs-on: self-hosted", text)
        self.assertIn("actions/checkout@v4", text)
        self.assertIn("actions/setup-node@v4", text)
        self.assertIn("adb devices", text)
        self.assertIn("sys.boot_completed", text)
        self.assertIn("./scripts/bootstrap.sh", text)
        self.assertIn("./scripts/verify-patches.sh", text)
        self.assertIn("./scripts/apply-patches.sh", text)
        self.assertIn("./scripts/test-extension-runtime.sh", text)
        self.assertNotIn("pull_request_target", text)


if __name__ == "__main__":
    unittest.main()
