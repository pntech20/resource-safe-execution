import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
FAST_INSTALL = (
    "npx --yes skills@1.5.20 add pntech20/resource-safe-execution "
    "--skill resource-safe-execution --copy"
)


class GrowthSurfaceTests(unittest.TestCase):
    def test_readme_first_screen_is_outcome_led(self):
        text = README.read_text(encoding="utf-8")
        first_screen = "\n".join(text.splitlines()[:65])
        self.assertIn(
            "Let your AI agent run heavy jobs—without freezing your workstation.",
            first_screen,
        )
        self.assertIn(FAST_INSTALL, first_screen.replace("`\\\n", " "))
        self.assertIn("No telemetry", first_screen)
        self.assertIn("Watch the 30-second proof", first_screen)

    def test_readme_discloses_installer_telemetry_boundary(self):
        text = README.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(
                r"skills CLI.*anonymous.*install telemetry.*"
                r"Resource Safe Execution.*no telemetry",
                re.IGNORECASE | re.DOTALL,
            ),
        )

    def test_readme_keeps_audited_release_route(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn(
            "https://github.com/pntech20/resource-safe-execution/"
            "tree/v0.1.0/skills/resource-safe-execution",
            text,
        )
        self.assertIn("skill-manifest.json", text)
        self.assertIn("SHA256SUMS", text)
