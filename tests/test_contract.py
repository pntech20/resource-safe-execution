import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "resource-safe-execution"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return simple scalar YAML fields and Markdown body."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        return {}, text

    fields: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("\"'")
    return fields, "\n".join(lines[closing_index + 1 :])


def markdown_targets(text: str) -> list[str]:
    """Return relative local link targets, excluding URL schemes."""
    targets = []
    for target in re.findall(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)", text):
        target = target.split("#", 1)[0]
        if target and not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            targets.append(target)
    return targets


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        cls.frontmatter, cls.body = parse_frontmatter(cls.skill_text)

    def test_frontmatter_is_portable_and_matches_folder(self) -> None:
        expected_fields = {"name", "description"}
        self.assertEqual(expected_fields, set(self.frontmatter))
        self.assertEqual(SKILL_DIR.name, self.frontmatter["name"])
        description = self.frontmatter["description"]
        self.assertGreaterEqual(len(description), 1)
        self.assertLessEqual(len(description), 1_024)

    def test_body_is_complete_and_bounded(self) -> None:
        forbidden_fragments = (
            "allowed-tools:",
            "$ARGUMENTS",
            "${CLAUDE_SKILL_DIR}",
            "taskkill /IM",
            "Stop-Process -Name",
            "killall ",
            "pkill ",
        )
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, self.skill_text)
        self.assertNotRegex(
            self.skill_text,
            re.compile(r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b", re.IGNORECASE),
        )
        self.assertLess(len(self.body.splitlines()), 500)
        self.assertLess(len(self.body.split()), 5_000)

    def test_required_direct_links_exist(self) -> None:
        required_links = (
            "scripts/resource_probe.py",
            "references/gpu-selection.md",
            "references/linux.md",
            "references/macos.md",
            "references/process-lifecycle.md",
            "references/windows.md",
        )
        targets = markdown_targets(self.body)
        for required_link in required_links:
            self.assertIn(required_link, targets)

        for target in targets:
            posix_target = PurePosixPath(target)
            self.assertFalse(posix_target.is_absolute(), target)
            self.assertNotIn("..", posix_target.parts, target)
            self.assertTrue((SKILL_DIR / Path(*posix_target.parts)).is_file(), target)

    def test_openai_metadata_is_ui_only_and_exact(self) -> None:
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Resource Safe Execution"', metadata)
        self.assertIn('short_description: "Run resource-heavy tasks safely"', metadata)
        self.assertIn(
            'default_prompt: "Use $resource-safe-execution to preflight this '
            'resource-intensive task and choose a safe execution profile."',
            metadata,
        )
        self.assertNotIn("display_name:", self.skill_text)
        self.assertNotIn("default_prompt:", self.skill_text)

    def test_evals_match_committed_scenario_contract(self) -> None:
        fixture = json.loads(
            (REPO_ROOT / "tests" / "fixtures" / "behavior-scenarios.json").read_text(
                encoding="utf-8"
            )
        )
        evals_path = SKILL_DIR / "evals" / "evals.json"
        self.assertTrue(evals_path.is_file(), str(evals_path))
        evals = json.loads(evals_path.read_text(encoding="utf-8"))
        self.assertEqual("1.0", evals["schema_version"])
        self.assertEqual({"present": 2, "partial": 1, "absent": 0}, evals["scoring"])

        fixture_contract = [
            (scenario["id"], scenario["required_signals"])
            for scenario in fixture["scenarios"]
        ]
        eval_contract = [
            (scenario["id"], scenario["required_signals"])
            for scenario in evals["scenarios"]
        ]
        self.assertEqual(fixture_contract, eval_contract)
        self.assertNotIn("response", json.dumps(evals).lower())

    def test_cleanup_contract_requires_scoped_evidence_and_refusal(self) -> None:
        normalized = " ".join(self.body.split()).lower()
        required_clauses = (
            "locate the task-scoped ownership record",
            "identify its owned root and group",
            "verify the root pid plus start identity",
            "invoke only the recorded graceful cleanup and owned-group or "
            "owned-tree termination apis",
            "if any step lacks evidence, refuse termination",
        )
        for clause in required_clauses:
            with self.subTest(clause=clause):
                self.assertIn(clause, normalized)
        self.assertIn("then verify exit", normalized)

    def test_evaluation_manifest_hashes_every_artifact_and_provenance_field(
        self,
    ) -> None:
        manifest_path = (
            REPO_ROOT / "docs" / "evaluations" / "2026-07-24-manifest.json"
        )
        self.assertTrue(manifest_path.is_file(), str(manifest_path))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("1.0", manifest["schema_version"])
        self.assertEqual("2026-07-24", manifest["evaluation_date"])
        self.assertEqual("Codex collaboration API", manifest["harness"])
        self.assertEqual("/root/task6_forward_test", manifest["scorer_identity"])

        self.assertNotIn("canonical_skill", manifest)
        self.assertEqual(
            "skills/resource-safe-execution/SKILL.md",
            manifest["evaluated_skill_path"],
        )

        fixture = json.loads(
            (REPO_ROOT / "tests" / "fixtures" / "behavior-scenarios.json").read_text(
                encoding="utf-8"
            )
        )
        prompts = {
            scenario["id"]: scenario["prompt"]
            for scenario in fixture["scenarios"]
        }
        evaluations = manifest["evaluations"]
        self.assertEqual(set(prompts), {
            evaluation["scenario_id"] for evaluation in evaluations
        })
        self.assertEqual(len(prompts), len(evaluations))

        expected_commits = {
            "concurrency-pressure": "4f87a309675bc5529c65e44f9acdfaa3d19a731f",
            "renderer-pressure": "4f87a309675bc5529c65e44f9acdfaa3d19a731f",
            "cleanup-pressure": "c801ea86c328eb7886e767a4a836dccf46290405",
            "gpu-assumption": "4f87a309675bc5529c65e44f9acdfaa3d19a731f",
        }
        unavailable_metadata = "not captured by collaboration API"
        for evaluation in evaluations:
            with self.subTest(scenario=evaluation["scenario_id"]):
                scenario_id = evaluation["scenario_id"]
                evaluated_commit = evaluation["evaluated_skill_commit"]
                self.assertEqual(
                    expected_commits[scenario_id],
                    evaluated_commit,
                )
                evaluated_blob = subprocess.run(
                    [
                        "git",
                        "show",
                        f"{evaluated_commit}:{manifest['evaluated_skill_path']}",
                    ],
                    cwd=REPO_ROOT,
                    check=True,
                    capture_output=True,
                ).stdout
                self.assertEqual(
                    hashlib.sha256(evaluated_blob).hexdigest(),
                    evaluation["evaluated_skill_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(
                        prompts[scenario_id].encode("utf-8")
                    ).hexdigest(),
                    evaluation["prompt_sha256"],
                )
                response_relative = PurePosixPath(evaluation["response_path"])
                self.assertFalse(response_relative.is_absolute())
                self.assertNotIn("..", response_relative.parts)
                response_path = REPO_ROOT / Path(*response_relative.parts)
                self.assertTrue(response_path.is_file())
                self.assertEqual(
                    hashlib.sha256(response_path.read_bytes()).hexdigest(),
                    evaluation["response_sha256"],
                )
                self.assertRegex(evaluation["evaluator_task_id"], r"^/root/")
                self.assertEqual(unavailable_metadata, evaluation["model"])
                self.assertEqual(
                    unavailable_metadata,
                    evaluation["reasoning_effort"],
                )


if __name__ == "__main__":
    unittest.main()
