import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0"
TAG = f"v{VERSION}"


class ReleaseReadinessTests(unittest.TestCase):
    def test_public_version_surfaces_match(self):
        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(codex["version"], VERSION)
        self.assertEqual(claude["version"], VERSION)
        self.assertEqual(marketplace["plugins"][0]["version"], VERSION)

    def test_readme_pins_current_release(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            f"github.com/pntech20/resource-safe-execution/tree/{TAG}/"
            "skills/resource-safe-execution",
            readme,
        )
        self.assertIn(f"The current release is `{TAG}`.", readme)
        self.assertNotIn("The release is `v0.1.0`.", readme)

    def test_compatibility_separates_package_and_payload_versions(self):
        compatibility = (ROOT / "docs" / "compatibility.md").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "The current package release is `v0.2.0`.",
            compatibility,
        )
        self.assertIn(
            "canonical skill payload remains the checksum-audited "
            "`v0.1.0` payload",
            compatibility,
        )

    def test_release_notes_define_scope_and_install(self):
        notes = (ROOT / "docs" / "releases" / f"{TAG}.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("# Resource Safe Execution v0.2.0", notes)
        self.assertIn("packaging and distribution release", notes)
        self.assertIn("canonical nine-file skill payload is unchanged", notes)
        self.assertIn("No new client-runtime compatibility claim", notes)
        self.assertIn(
            f"github.com/pntech20/resource-safe-execution/tree/{TAG}/"
            "skills/resource-safe-execution",
            notes,
        )


if __name__ == "__main__":
    unittest.main()
