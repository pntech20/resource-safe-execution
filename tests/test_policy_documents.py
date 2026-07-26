import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PolicyDocumentTests(unittest.TestCase):
    def test_support_routes_each_request_type(self):
        text = (ROOT / "SUPPORT.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "bug report",
            "compatibility report",
            "discussions",
            "security advisories",
        ):
            self.assertIn(phrase, text)

    def test_privacy_preserves_skill_and_cli_boundaries(self):
        text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "no network access",
            "no telemetry",
            "skills cli",
            "anonymous",
            "opt-out",
            "github",
            "openai",
            "anthropic",
            "google",
            "social platforms",
        ):
            self.assertIn(phrase, text)

    def test_terms_preserves_license_and_disclaimer_boundaries(self):
        text = (ROOT / "TERMS.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "mit",
            "license controls",
            "guidance",
            "availability",
            "performance guarantee",
            "third-party services",
            "separate terms",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("by using", text)


if __name__ == "__main__":
    unittest.main()
