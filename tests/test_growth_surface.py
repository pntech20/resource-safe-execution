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
        self.assertIn("Watch the 38-second proof", first_screen)

    def test_readme_discloses_installer_telemetry_boundary(self):
        text = README.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(
                r"`skills` CLI.*anonymous.*install telemetry.*"
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

    def test_openai_plugin_points_to_canonical_skills(self):
        path = ROOT / ".codex-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "resource-safe-execution")
        self.assertEqual(data["version"], "0.2.0")
        self.assertEqual(data["skills"], "./skills/")
        self.assertTrue((ROOT / data["skills"]).resolve().is_dir())
        self.assertEqual(data["author"]["name"], "pntech20")
        interface = data["interface"]
        self.assertEqual(interface["displayName"], "Resource Safe Execution")
        self.assertEqual(interface["developerName"], "pntech20")
        self.assertEqual(len(interface["defaultPrompt"]), 3)
        self.assertTrue(interface["websiteURL"].startswith("https://"))
        self.assertTrue(interface["privacyPolicyURL"].startswith("https://"))
        self.assertTrue(interface["termsOfServiceURL"].startswith("https://"))

    def test_claude_plugin_metadata_is_complete(self):
        path = ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "resource-safe-execution")
        self.assertEqual(data["version"], "0.2.0")
        self.assertEqual(data["license"], "MIT")
        self.assertEqual(
            data["repository"],
            "https://github.com/pntech20/resource-safe-execution",
        )

    def test_claude_marketplace_uses_repository_root_plugin(self):
        path = ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "pntech20-agent-skills")
        self.assertEqual(data["owner"]["name"], "pntech20")
        self.assertEqual(len(data["plugins"]), 1)
        plugin = data["plugins"][0]
        self.assertEqual(plugin["name"], "resource-safe-execution")
        self.assertEqual(plugin["source"], "./")
        self.assertEqual(plugin["version"], "0.2.0")
