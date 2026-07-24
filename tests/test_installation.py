import shutil
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from tests.test_contract import markdown_targets, parse_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "resource-safe-execution"

PROJECT_TARGETS = {
    "codex": Path(".agents/skills"),
    "claude-code": Path(".claude/skills"),
    "antigravity": Path(".agents/skills"),
    "cursor": Path(".cursor/skills"),
    "opencode": Path(".opencode/skills"),
}


def install_copy(source: Path, destination_root: Path) -> Path:
    """Copy one skill folder into an otherwise clean client skills directory."""
    installed = destination_root / source.name
    shutil.copytree(source, installed)
    return installed


class InstallationTests(unittest.TestCase):
    def test_clean_project_copies_preserve_contract_and_local_links(self) -> None:
        for client, relative_root in PROJECT_TARGETS.items():
            with self.subTest(client=client), tempfile.TemporaryDirectory() as temporary:
                project = Path(temporary)
                installed = install_copy(SKILL_DIR, project / relative_root)
                skill_text = (installed / "SKILL.md").read_text(encoding="utf-8")
                frontmatter, body = parse_frontmatter(skill_text)

                self.assertEqual({"name", "description"}, set(frontmatter))
                self.assertEqual(installed.name, frontmatter["name"])
                for target in markdown_targets(body):
                    posix_target = PurePosixPath(target)
                    self.assertFalse(posix_target.is_absolute(), target)
                    self.assertNotIn("..", posix_target.parts, target)
                    self.assertTrue(
                        (installed / Path(*posix_target.parts)).is_file(),
                        f"{client}: {target}",
                    )


if __name__ == "__main__":
    unittest.main()
