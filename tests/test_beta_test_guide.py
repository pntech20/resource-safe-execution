import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "launch" / "beta-test.md"
CANONICAL_INSTALL = (
    "npx --yes skills@1.5.20 add pntech20/resource-safe-execution "
    "--skill resource-safe-execution --copy"
)
ACTIVATION_PROMPT = (
    "Before running this build and eight browser workers, inspect my machine, "
    "choose a safe profile, track every process you launch, and clean up only "
    "your owned tree."
)


class BetaTestGuideTests(unittest.TestCase):
    def read_guide(self) -> str:
        return GUIDE.read_text(encoding="utf-8")

    def test_guide_has_the_15_minute_procedure_and_activation_copy(self):
        text = self.read_guide()
        normalized = re.sub(r"\s+", " ", text)
        self.assertEqual(text.splitlines()[0], "# 15-minute beta test")
        self.assertEqual(
            re.findall(r"^(\d+)\. ", text, flags=re.MULTILINE),
            [str(number) for number in range(1, 9)],
        )
        self.assertIn(CANONICAL_INSTALL, text)
        self.assertIn(ACTIVATION_PROMPT, normalized)

    def test_guide_requires_redaction_and_quote_consent(self):
        text = self.read_guide()
        lowered = text.lower()
        for private_value in (
            "command lines",
            "paths",
            "tokens",
            "usernames",
            "machine names",
            "unrelated processes",
        ):
            self.assertIn(private_value, lowered)
        self.assertRegex(
            lowered,
            r"- \[ \].*opt in.*anonymized quote",
        )
        self.assertIn("do not collect tester identities", lowered)
        self.assertIn("github issues are public", lowered)
        self.assertIn("reporter's account identity", lowered)
        self.assertIn("must not copy the reporter's handle", lowered)

    def test_guide_records_only_threshold_met_evidence_and_aggregate_counts(self):
        text = self.read_guide()
        lowered = text.lower()
        for evidence_field in (
            "client version",
            "operating system",
            "install method",
            "activation evidence",
            "observed outcome",
        ):
            self.assertIn(evidence_field, lowered)
        self.assertIn("community-reported", lowered)
        self.assertIn("maintainer-reproduced", lowered)
        self.assertIn("aggregate counts only", lowered)
        self.assertIn(
            "no beta outcomes or compatibility results have been collected",
            lowered,
        )

    def test_guide_bounds_recruitment_and_pauses_on_defects(self):
        text = self.read_guide()
        for target in (
            "5–8 Codex users",
            "5–8 Claude Code users",
            "4–6 Antigravity users",
            "4–8 users across Cursor, Gemini CLI, OpenCode, or another "
            "compatible client",
        ):
            self.assertIn(target, text)
        lowered = text.lower()
        self.assertIn("existing professional or community relationships", lowered)
        self.assertIn("do not mass-message strangers", lowered)
        self.assertIn("one reproducible issue", lowered)
        self.assertIn("before inviting the next batch", lowered)
        self.assertIn("security defects pause all recruiting", lowered)
        self.assertIn(
            "safety or compatibility defect pauses promotion",
            lowered,
        )


if __name__ == "__main__":
    unittest.main()
