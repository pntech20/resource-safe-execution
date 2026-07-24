import contextlib
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock

from tests.test_contract import markdown_targets, parse_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "resource-safe-execution"
MANIFEST_PATH = REPO_ROOT / "skill-manifest.json"
SHA256SUMS_PATH = REPO_ROOT / "SHA256SUMS"

PROJECT_TARGETS = {
    "codex": Path(".agents/skills"),
    "claude-code": Path(".claude/skills"),
    "antigravity": Path(".agents/skills"),
    "cursor": Path(".cursor/skills"),
    "opencode": Path(".opencode/skills"),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_hashes() -> dict[PurePosixPath, str]:
    if not MANIFEST_PATH.is_file():
        raise AssertionError(f"missing installation manifest: {MANIFEST_PATH}")
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        raise ValueError("unsupported installation manifest schema")
    entries = payload.get("files")
    if not isinstance(entries, list):
        raise ValueError("installation manifest files must be a list")
    hashes: dict[PurePosixPath, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("installation manifest entry must be an object")
        relative = PurePosixPath(str(entry.get("path", "")))
        digest = entry.get("sha256")
        if (
            relative.is_absolute()
            or not relative.parts
            or ".." in relative.parts
            or not isinstance(digest, str)
            or len(digest) != 64
        ):
            raise ValueError("invalid installation manifest entry")
        hashes[relative] = digest
    if len(hashes) != len(entries):
        raise ValueError("duplicate installation manifest path")
    return hashes


def payload_paths(source: Path) -> set[PurePosixPath]:
    if source.is_symlink():
        raise ValueError(f"source root is a symlink: {source}")
    paths: set[PurePosixPath] = set()
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed in payload: {relative.as_posix()}")
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_file():
            paths.add(PurePosixPath(relative.as_posix()))
        elif not path.is_dir():
            raise ValueError(
                f"non-regular payload entry: {relative.as_posix()}"
            )
    return paths


def install_copy(source: Path, destination_root: Path) -> Path:
    """Verify and copy exactly the reviewed canonical skill payload."""
    expected = manifest_hashes()
    actual = payload_paths(source)
    if actual != set(expected):
        unexpected = sorted(str(path) for path in actual - set(expected))
        missing = sorted(str(path) for path in set(expected) - actual)
        raise ValueError(
            f"payload differs from manifest; unexpected={unexpected}; missing={missing}"
        )

    for relative, expected_hash in expected.items():
        source_path = source / Path(*relative.parts)
        if not source_path.is_file() or source_path.is_symlink():
            raise ValueError(f"payload entry is not a regular file: {relative}")
        if sha256_file(source_path) != expected_hash:
            raise ValueError(f"hash mismatch for {relative}")

    installed = destination_root / source.name
    if installed.exists() or installed.is_symlink():
        raise FileExistsError(f"destination already exists: {installed}")
    for relative in expected:
        source_path = source / Path(*relative.parts)
        installed_path = installed / Path(*relative.parts)
        installed_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, installed_path)
    return installed


class InstallationTests(unittest.TestCase):
    def test_manifest_and_sha256sums_cover_exactly_nine_canonical_files(
        self,
    ) -> None:
        expected = manifest_hashes()
        self.assertTrue(SHA256SUMS_PATH.is_file(), str(SHA256SUMS_PATH))
        self.assertEqual(9, len(expected))
        self.assertEqual(expected, {
            relative: sha256_file(SKILL_DIR / Path(*relative.parts))
            for relative in expected
        })

        sums: dict[PurePosixPath, str] = {}
        for line in SHA256SUMS_PATH.read_text(encoding="utf-8").splitlines():
            digest, relative_text = line.split("  ", 1)
            prefix = PurePosixPath("skills/resource-safe-execution")
            repository_relative = PurePosixPath(relative_text)
            self.assertEqual(prefix, PurePosixPath(*repository_relative.parts[:2]))
            relative = PurePosixPath(*repository_relative.parts[2:])
            sums[relative] = digest
        self.assertEqual(expected, sums)

    def test_hashed_payload_and_evidence_use_checkout_stable_line_endings(
        self,
    ) -> None:
        attributes_path = REPO_ROOT / ".gitattributes"
        self.assertTrue(attributes_path.is_file(), str(attributes_path))
        attributes = attributes_path.read_text(encoding="utf-8").splitlines()
        self.assertIn(
            "skills/resource-safe-execution/** text eol=lf",
            attributes,
        )
        self.assertIn("docs/evaluations/raw/** text eol=lf", attributes)
        self.assertIn("skill-manifest.json text eol=lf", attributes)
        self.assertIn("SHA256SUMS text eol=lf", attributes)

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
                installed_hashes = {
                    PurePosixPath(path.relative_to(installed).as_posix()):
                    sha256_file(path)
                    for path in installed.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(manifest_hashes(), installed_hashes)

    def test_changed_canonical_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / SKILL_DIR.name
            shutil.copytree(
                SKILL_DIR,
                source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            (source / "SKILL.md").write_text("changed", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "hash mismatch for SKILL.md"):
                install_copy(source, root / "destination")

    def test_symlinked_canonical_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / SKILL_DIR.name
            shutil.copytree(
                SKILL_DIR,
                source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            canonical = source / "references" / "linux.md"
            target = root / "outside-linux.md"
            shutil.copyfile(canonical, target)
            canonical.unlink()
            try:
                canonical.symlink_to(target)
            except OSError as exc:
                shutil.copyfile(target, canonical)
                original_is_symlink = Path.is_symlink

                def simulated_symlink(path: Path) -> bool:
                    return path == canonical or original_is_symlink(path)

                with mock.patch.object(
                    Path,
                    "is_symlink",
                    autospec=True,
                    side_effect=simulated_symlink,
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "symlink is not allowed",
                    ):
                        install_copy(source, root / "destination")
            else:
                with self.assertRaisesRegex(ValueError, "symlink is not allowed"):
                    install_copy(source, root / "destination")

    def test_symlinked_source_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_source = root / "real-source"
            shutil.copytree(
                SKILL_DIR,
                real_source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            source = root / SKILL_DIR.name
            try:
                source.symlink_to(real_source, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlink creation unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "source root is a symlink"):
                install_copy(source, root / "destination")

    def test_source_root_symlink_check_precedes_descendant_traversal(self) -> None:
        seen: list[Path] = []

        def simulated_symlink(path: Path) -> bool:
            seen.append(path)
            return path == SKILL_DIR

        with mock.patch.object(
            Path,
            "is_symlink",
            autospec=True,
            side_effect=simulated_symlink,
        ):
            with self.assertRaisesRegex(ValueError, "source root is a symlink"):
                payload_paths(SKILL_DIR)

        self.assertEqual([SKILL_DIR], seen)

    def test_symlinked_pycache_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / SKILL_DIR.name
            shutil.copytree(
                SKILL_DIR,
                source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            target = root / "outside-cache"
            target.mkdir()
            cache = source / "scripts" / "__pycache__"
            try:
                cache.symlink_to(target, target_is_directory=True)
            except OSError:
                cache.mkdir()
                original_is_symlink = Path.is_symlink

                def simulated_symlink(path: Path) -> bool:
                    return path == cache or original_is_symlink(path)

                symlink_patch = mock.patch.object(
                    Path,
                    "is_symlink",
                    autospec=True,
                    side_effect=simulated_symlink,
                )
            else:
                symlink_patch = contextlib.nullcontext()

            with symlink_patch:
                with self.assertRaisesRegex(ValueError, "symlink is not allowed"):
                    payload_paths(source)

    def test_symlinked_pyc_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / SKILL_DIR.name
            shutil.copytree(
                SKILL_DIR,
                source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            target = root / "outside.pyc"
            target.write_bytes(b"outside")
            cached = source / "scripts" / "resource_probe.pyc"
            try:
                cached.symlink_to(target)
            except OSError:
                shutil.copyfile(target, cached)
                original_is_symlink = Path.is_symlink

                def simulated_symlink(path: Path) -> bool:
                    return path == cached or original_is_symlink(path)

                symlink_patch = mock.patch.object(
                    Path,
                    "is_symlink",
                    autospec=True,
                    side_effect=simulated_symlink,
                )
            else:
                symlink_patch = contextlib.nullcontext()

            with symlink_patch:
                with self.assertRaisesRegex(ValueError, "symlink is not allowed"):
                    payload_paths(source)

    def test_unexpected_ordinary_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / SKILL_DIR.name
            shutil.copytree(
                SKILL_DIR,
                source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            (source / "unexpected.txt").write_text("unexpected", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unexpected.txt"):
                install_copy(source, root / "destination")


if __name__ == "__main__":
    unittest.main()
