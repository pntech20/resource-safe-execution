import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "docs" / "launch" / "marketplace-submission.md"

POSITIVE_CASES = (
    "Run eight browser workers on this laptop.",
    "Choose safe parallelism for this build.",
    "Check whether my ML workload really uses the GPU.",
    "Stop the emulator and only processes you started.",
    "Inspect disk pressure before generating large artifacts.",
)

NEGATIVE_CASES = (
    "Rewrite this function for readability.",
    "Summarize this Markdown file.",
    "Rename this CSS class.",
)


class MarketplaceReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SUBMISSION.is_file(),
            f"missing marketplace readiness guide: {SUBMISSION}",
        )
        self.text = SUBMISSION.read_text(encoding="utf-8")

    def test_openai_readiness_has_every_submission_input(self):
        required = (
            "## OpenAI readiness checklist",
            "Verified publisher identity",
            "Apps Management: Write permission",
            "Plugin name",
            "Short description",
            "Long description",
            "Logo",
            "Category",
            "Website URL",
            "Support URL",
            "Privacy URL",
            "Terms URL",
            "Skill bundle/ZIP",
            "Starter prompts",
            "Availability and release notes",
            "Automated policy/security scan",
        )
        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, self.text)

        for url in (
            "https://github.com/pntech20/resource-safe-execution",
            "https://github.com/pntech20/resource-safe-execution/blob/main/SUPPORT.md",
            "https://github.com/pntech20/resource-safe-execution/blob/main/PRIVACY.md",
            "https://github.com/pntech20/resource-safe-execution/blob/main/TERMS.md",
        ):
            with self.subTest(url=url):
                self.assertIn(url, self.text)

    def test_claude_readiness_keeps_unavailable_validation_explicit(self):
        required = (
            "## Claude readiness checklist",
            "`claude plugin validate .`",
            "`claude --plugin-dir .`",
            "Self-hosted marketplace install",
            "Repository",
            "Homepage",
            "License",
            "Author",
            "Version",
            "Public community-directory submission form",
            "`claude-plugins-official` has no application process",
        )
        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, self.text)

        self.assertGreaterEqual(self.text.count("Unavailable / not run"), 3)

    def test_activation_matrix_uses_exact_cases_and_expected_boundaries(self):
        for index, prompt in enumerate(POSITIVE_CASES, start=1):
            with self.subTest(kind="positive", prompt=prompt):
                self.assertIn(f"| P{index} | {prompt} |", self.text)
        for index, prompt in enumerate(NEGATIVE_CASES, start=1):
            with self.subTest(kind="negative", prompt=prompt):
                self.assertIn(f"| N{index} | {prompt} |", self.text)

        self.assertIn(
            "Positive cases must activate resource-safe planning.",
            self.text,
        )
        self.assertIn(
            "Negative cases must not load the skill solely because they are "
            "ordinary code edits.",
            self.text,
        )

    def test_evidence_record_requires_version_output_and_truthful_status(self):
        evidence = self.text.split("## Validation evidence record", 1)[1]
        for heading in (
            "Status",
            "Client/tool version",
            "Command or action",
            "Exit code",
            "Exact output",
            "Date",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, evidence)

        self.assertIn("Not submitted", self.text)
        self.assertIn("Not accepted", self.text)
        self.assertIn("No approval SLA is promised.", self.text)

    def test_local_validator_evidence_does_not_upgrade_runtime_claims(self):
        evidence = self.text.split("## Validation evidence record", 1)[1]
        for validator in (
            "OpenAI local plugin package validator",
            "Canonical repository skill validator",
            "Agent Skills quick validator",
        ):
            self.assertIn(validator, evidence)
        self.assertGreaterEqual(evidence.count("Passed—format/package only"), 3)
        self.assertIn("version not exposed", evidence)
        self.assertIn("do not establish", evidence)
        self.assertIn("client runtime behavior", evidence)

    def test_github_skill_publisher_dry_run_records_advisory_warnings(self):
        evidence = self.text.split("## Validation evidence record", 1)[1]
        self.assertIn("GitHub skill publisher dry-run", evidence)
        self.assertIn("Passed with warnings—format/package only", evidence)
        self.assertIn("recommended field missing: license", evidence)
        self.assertIn("no active tag protection rulesets found", evidence)
        self.assertIn("checksum-audited v0.1.0", evidence)
        self.assertIn("repository-owner governance review", evidence)

    def test_account_holder_retains_identity_legal_and_submission_authority(self):
        authority = self.text.split("## Account-holder submission gate", 1)[1]
        for phrase in (
            "publisher identity",
            "legal links",
            "availability",
            "terms",
            "Platform submission portal",
            "public community plugin form",
        ):
            with self.subTest(phrase=phrase):
                self.assertRegex(authority, re.compile(phrase, re.IGNORECASE))

        self.assertIn("No external submission was performed.", authority)
        self.assertNotIn("will be accepted", self.text.lower())


if __name__ == "__main__":
    unittest.main()
