from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "test-extension"


class FixtureContractTest(unittest.TestCase):
    def test_manifest_contract(self) -> None:
        manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["name"], "Brave Android Extensions MVP Fixture")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertIn("storage", manifest["permissions"])
        self.assertEqual(manifest["background"]["service_worker"], "background.js")
        self.assertEqual(manifest["action"]["default_popup"], "popup.html")
        self.assertIn("http://match.test/*", manifest["host_permissions"])
        self.assertEqual(manifest["content_scripts"][0]["matches"], ["http://match.test/*"])

    def test_content_script_marker_contract(self) -> None:
        text = (FIXTURE / "content_script.js").read_text(encoding="utf-8")
        self.assertIn("brave-android-extension-fixture", text)
        self.assertIn("fixture-content-script-ok", text)

    def test_background_message_and_storage_contract(self) -> None:
        text = (FIXTURE / "background.js").read_text(encoding="utf-8")
        self.assertIn("fixture-ping", text)
        self.assertIn("fixture-pong", text)
        self.assertIn("fixtureSeen", text)
        self.assertIn("chrome.storage.local.set", text)

    def test_popup_reads_fixture_state(self) -> None:
        html = (FIXTURE / "popup.html").read_text(encoding="utf-8")
        js = (FIXTURE / "popup.js").read_text(encoding="utf-8")
        self.assertIn('id="state"', html)
        self.assertIn("popup.js", html)
        self.assertIn("fixtureSeen", js)
        self.assertIn("chrome.storage.local.get", js)


if __name__ == "__main__":
    unittest.main()
