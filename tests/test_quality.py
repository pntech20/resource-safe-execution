import compileall
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "resource-safe-execution"
EXPECTED_README_HEADINGS = [
    "# Resource Safe Execution",
    "## Why",
    "## What it does",
    "## Safety guarantees",
    "## Install",
    "## Agent compatibility",
    "## Run the probe directly",
    "## Validate",
    "## Contributing and security",
    "## License",
]


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return [
        REPO_ROOT / Path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    ]


class RepositoryQualityTests(unittest.TestCase):
    def test_all_tracked_files_are_utf8_without_whitespace_defects(self) -> None:
        for path in tracked_files():
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_bytes().decode("utf-8")
                for line_number, line in enumerate(text.splitlines(), start=1):
                    self.assertEqual(
                        line.rstrip(),
                        line,
                        f"{path}:{line_number}: trailing whitespace",
                    )
                    self.assertFalse(
                        line.startswith("\t"),
                        f"{path}:{line_number}: tab indentation",
                    )

    def test_python_files_compile(self) -> None:
        self.assertTrue(
            compileall.compile_dir(
                REPO_ROOT / "skills",
                quiet=1,
                force=True,
            )
        )
        self.assertTrue(
            compileall.compile_dir(
                REPO_ROOT / "tests",
                quiet=1,
                force=True,
            )
        )

    def test_readme_has_required_sections_and_project_links(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        headings = re.findall(r"^#{1,2} .+$", readme, flags=re.MULTILINE)
        self.assertEqual(EXPECTED_README_HEADINGS, headings)
        required_links = {
            "LICENSE",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "docs/compatibility.md",
            "skills/resource-safe-execution",
        }
        linked_targets = {
            target.split("#", 1)[0]
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
        }
        self.assertTrue(required_links <= linked_targets)
        for target in required_links:
            self.assertTrue((REPO_ROOT / target).exists(), target)

    def test_documentation_qualifies_compatibility_evidence(self) -> None:
        compatibility_path = REPO_ROOT / "docs" / "compatibility.md"
        self.assertTrue(compatibility_path.is_file(), str(compatibility_path))
        compatibility = compatibility_path.read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        documentation = f"{readme}\n{compatibility}".lower()
        self.assertIn("format and install validation", documentation)
        self.assertIn("client runtime validation", documentation)
        self.assertRegex(
            documentation,
            r"(no|not|without) (?:actual |proprietary )?client runtime validation",
        )

    def test_repository_validator_accepts_the_canonical_skill(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tests" / "validate_skill.py"),
                str(SKILL_DIR),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_ci_is_pinned_and_runs_all_required_checks(self) -> None:
        workflow_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow_path.is_file(), str(workflow_path))
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", workflow)
        self.assertIn(
            "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
            workflow,
        )
        self.assertNotRegex(workflow, r"uses:\s+[^@\s]+@(?![0-9a-f]{40}\b)")
        self.assertIn("python -m compileall skills tests", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn(
            "python tests/validate_skill.py skills/resource-safe-execution",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
