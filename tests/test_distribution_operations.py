import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
METRICS = ROOT / "docs" / "launch" / "metrics.csv"
MATRIX = ROOT / "docs" / "launch" / "community-matrix.md"
LISTING = (
    "https://skills.sh/pntech20/resource-safe-execution/"
    "resource-safe-execution"
)
BADGE = (
    "[![skills.sh installs]"
    "(https://skills.sh/b/pntech20/resource-safe-execution)]"
    f"({LISTING})"
)


class DistributionOperationsTests(unittest.TestCase):
    def test_readme_links_live_listing_and_public_policies(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn(BADGE, readme)
        self.assertIn(
            "[Support](SUPPORT.md) · [Privacy](PRIVACY.md) · "
            "[Terms](TERMS.md)",
            readme,
        )

    def test_metrics_ledger_has_verified_day_zero_aggregates(self):
        self.assertTrue(METRICS.is_file())
        with METRICS.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        self.assertEqual(
            reader.fieldnames,
            [
                "date",
                "skills_sh_installs",
                "github_stars",
                "github_forks",
                "release_downloads",
                "qualified_impressions",
                "repository_visits",
                "beta_workloads",
                "notes",
            ],
        )
        self.assertEqual(len(rows), 1)
        baseline = rows[0]
        self.assertEqual(baseline["date"], "2026-07-25")
        self.assertEqual(baseline["skills_sh_installs"], "0")
        self.assertEqual(baseline["github_stars"], "1")
        self.assertEqual(baseline["github_forks"], "0")
        self.assertEqual(baseline["release_downloads"], "0")
        self.assertEqual(baseline["qualified_impressions"], "0")
        self.assertEqual(baseline["repository_visits"], "0")
        self.assertEqual(baseline["beta_workloads"], "0")
        self.assertIn("public counters checked", baseline["notes"].lower())

        forbidden_fields = {
            "username",
            "email",
            "ip",
            "client_id",
            "machine",
        }
        self.assertTrue(forbidden_fields.isdisjoint(reader.fieldnames))

    def test_community_matrix_has_rule_checked_channel_gates(self):
        self.assertTrue(MATRIX.is_file())
        matrix = MATRIX.read_text(encoding="utf-8")
        self.assertIn(
            "| Channel | Current rule URL | Eligible now? | "
            "Required disclosure/flair | Asset | Planned date | "
            "Published URL | Outcome |",
            matrix,
        )

        for channel in (
            "skills.sh",
            "GitHub",
            "X",
            "LinkedIn",
            "DEV",
            "Hashnode",
            "Show HN",
            "Product Hunt",
            "r/ClaudeAI",
            "r/ClaudeCode",
            "r/codex",
            "r/opensource",
            "Cursor forum",
            "VoltAgent/awesome-agent-skills",
            "ComposioHQ/awesome-claude-skills",
        ):
            self.assertIn(f"| {channel} |", matrix)

        for rule_url in (
            "https://help.x.com/en/rules-and-policies/authenticity",
            "https://www.linkedin.com/legal/professional-community-policies",
            "https://dev.to/code-of-conduct",
            "https://hashnode.com/code-of-conduct",
            "https://news.ycombinator.com/showhn.html",
            "https://help.producthunt.com/en/articles/3615694-community-guidelines",
            "https://forum.cursor.com/guidelines",
            "https://github.com/VoltAgent/awesome-agent-skills",
            "https://github.com/ComposioHQ/awesome-claude-skills/"
            "blob/master/CONTRIBUTING.md",
        ):
            self.assertIn(rule_url, matrix)

        claude_ai_row = next(
            line for line in matrix.splitlines() if line.startswith("| r/ClaudeAI |")
        )
        opensource_row = next(
            line for line in matrix.splitlines() if line.startswith("| r/opensource |")
        )
        show_hn_row = next(
            line for line in matrix.splitlines() if line.startswith("| Show HN |")
        )
        self.assertIn("DO NOT POST", claude_ai_row)
        self.assertIn("DO NOT POST", opensource_row)
        self.assertIn("human-written", show_hn_row)
        self.assertIn("manual account-holder", matrix)
        self.assertNotIn("ask for upvotes", matrix.lower())

    def test_community_matrix_locks_the_30_day_sequence(self):
        matrix = MATRIX.read_text(encoding="utf-8")
        for phase in (
            "Days 1–3",
            "Days 4–7",
            "Days 8–14",
            "Days 15–21",
            "Days 22–30",
        ):
            self.assertIn(phase, matrix)
        self.assertIn("500 qualified repository visits", matrix)
        self.assertIn("fewer than 150", matrix)
        self.assertIn("pause promotion", matrix)


if __name__ == "__main__":
    unittest.main()
