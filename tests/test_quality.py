import ast
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
    def test_probe_docstrings_match_qualified_write_and_profile_contract(
        self,
    ) -> None:
        probe_path = SKILL_DIR / "scripts" / "resource_probe.py"
        tree = ast.parse(probe_path.read_text(encoding="utf-8"))
        module_docstring = ast.get_docstring(tree) or ""
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        recommendation_docstring = (
            ast.get_docstring(functions["build_recommendation"]) or ""
        )

        self.assertIn("read-only host inspection", module_docstring)
        self.assertIn("selected profile", recommendation_docstring)
        self.assertNotIn("balanced default", recommendation_docstring)

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
            "skill-manifest.json",
            "SHA256SUMS",
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

    def test_release_plan_separates_fixture_and_hosted_ci_evidence(self) -> None:
        plan = (
            REPO_ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-07-24-resource-safe-execution-v1.md"
        ).read_text(encoding="utf-8")
        task_six = plan.split("### Task 6:", 1)[1]
        normalized_task_six = " ".join(task_six.split())
        self.assertIn(
            "Mark macOS and Linux as fixture-validated only. Mark them as "
            "CI-validated only after hosted CI succeeds.",
            normalized_task_six,
        )
        self.assertNotIn(
            "fixture- and CI-validated until hosted CI completes",
            task_six,
        )
        self.assertIn(
            "- [x] **Step 3: Validate clean-copy installation without "
            "overwriting existing data**",
            task_six,
        )
        for step in range(1, 6):
            with self.subTest(step=step):
                self.assertRegex(
                    task_six,
                    rf"- \[x\] \*\*Step {step}: [^*]+\*\*",
                )
        for step in (6, 7):
            with self.subTest(step=step):
                self.assertRegex(
                    task_six,
                    rf"- \[ \] \*\*Step {step}: [^*]+\*\*",
                )

    def test_documentation_records_bounded_child_and_output_lifecycle(self) -> None:
        paths = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "SECURITY.md",
            REPO_ROOT
            / "docs"
            / "superpowers"
            / "specs"
            / "2026-07-24-resource-safe-execution-design.md",
            REPO_ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-07-24-resource-safe-execution-v1.md",
        )
        for path in paths:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = " ".join(
                    path.read_text(encoding="utf-8").lower().split()
                )
                self.assertIn(
                    "never terminates pre-existing or unrelated processes",
                    text,
                )
                self.assertIn("timeout", text)
                self.assertIn("overflow", text)

        documentation = "\n".join(
            path.read_text(encoding="utf-8") for path in paths
        ).lower()
        self.assertIn("read-only host inspection", documentation)
        self.assertIn("optional output-file write", documentation)
        self.assertIn("create", documentation)
        self.assertIn("exclusively", documentation)

    def test_documentation_states_hardened_trust_and_platform_boundaries(
        self,
    ) -> None:
        paths = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "SECURITY.md",
            REPO_ROOT
            / "docs"
            / "superpowers"
            / "specs"
            / "2026-07-24-resource-safe-execution-design.md",
            REPO_ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-07-24-resource-safe-execution-v1.md",
        )
        documentation = " ".join(
            path.read_text(encoding="utf-8") for path in paths
        ).lower()
        required = (
            "native windows apis",
            "inherited path",
            "privileged system-directory mutation",
            "0.25-second cleanup grace",
            "descendant-held standard handles",
            "posix directory-handle-relative",
            "windows v0.1 requires stdout",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, documentation)

    def test_documentation_states_module_pipe_and_access_error_boundaries(
        self,
    ) -> None:
        paths = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "SECURITY.md",
            REPO_ROOT
            / "docs"
            / "superpowers"
            / "specs"
            / "2026-07-24-resource-safe-execution-design.md",
            REPO_ROOT
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-07-24-resource-safe-execution-v1.md",
        )
        documentation = " ".join(
            path.read_text(encoding="utf-8") for path in paths
        ).lower()
        required = (
            "psmodulepath",
            "retained captured bytes",
            "operating-system-bounded pipe buffers",
            "does not bound the total bytes",
            "error_access_denied",
            "error_privilege_not_held",
            "sharing and transient errors fail closed",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, documentation)

    def test_installation_docs_pin_reviewed_payload_and_convenience_route(
        self,
    ) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        compatibility = (
            REPO_ROOT / "docs" / "compatibility.md"
        ).read_text(encoding="utf-8")
        self.assertIn("skill-manifest.json", readme)
        self.assertIn("SHA256SUMS", readme)
        self.assertIn("safe default", readme.lower())
        self.assertIn("convenience-only", readme.lower())
        self.assertIn(
            "npx --yes skills@1.5.20 add "
            "https://github.com/pntech20/resource-safe-execution/tree/v0.1.0/"
            "skills/resource-safe-execution --skill resource-safe-execution --copy",
            readme,
        )
        self.assertIn(
            "sha512-lPl5KzMfTW+qwHFwc8t6R+wAqmdmSHw1+HWbGdJ/"
            "FZYbWLdB34bAZNFWiencM5DVoRaKAgXArmfTWMlNAbl9Gg==",
            compatibility,
        )
        self.assertIn(
            "https://github.com/vercel-labs/skills/releases/tag/v1.5.20",
            compatibility,
        )
        self.assertIn(
            "reject a symlinked source root and symlinked descendants",
            compatibility,
        )
        self.assertIn(
            "do not validate ancestors above the selected source root",
            compatibility,
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
        checkout_block = workflow.split("- name: Check out repository", 1)[1].split(
            "- name:", 1
        )[0]
        self.assertIn("fetch-depth: 0", checkout_block)
        self.assertIn(
            "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
            workflow,
        )
        self.assertNotRegex(workflow, r"uses:\s+[^@\s]+@(?![0-9a-f]{40}\b)")
        self.assertIn("python -m compileall skills tests", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn("- name: Smoke-test live JSON probe", workflow)
        smoke_block = workflow.split("- name: Smoke-test live JSON probe", 1)[
            1
        ].split("- name:", 1)[0]
        self.assertLess(
            workflow.index("- name: Run tests"),
            workflow.index("- name: Smoke-test live JSON probe"),
        )
        self.assertIn("timeout-minutes: 1", smoke_block)
        self.assertIn("--format json --sample-seconds 0.1", smoke_block)
        self.assertIn("json.load(sys.stdin)", smoke_block)
        self.assertIn(
            "python tests/validate_skill.py skills/resource-safe-execution",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
