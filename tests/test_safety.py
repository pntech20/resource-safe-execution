import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = (
    REPO_ROOT / "skills" / "resource-safe-execution" / "scripts" / "resource_probe.py"
)
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib", "socket", "ftplib", "smtplib"}
FORBIDDEN_CALLS = {"terminate", "send_signal"}
SENSITIVE_OUTPUT_KEYS = {
    "command_line",
    "cmdline",
    "environment",
    "username",
    "token",
    "network_destination",
}
DESTRUCTIVE_FRAGMENTS = {
    "taskkill",
    "stop-process",
    "killall",
    "pkill",
    "remove-item",
    "rm -",
    "del /",
    "format.com",
}
PACKAGE_MANAGER_COMMANDS = {
    "pip",
    "pip3",
    "apt",
    "apt-get",
    "dnf",
    "yum",
    "brew",
    "winget",
    "choco",
    "npm",
}


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def literal_strings(node: ast.AST) -> list[str]:
    return [
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]


class StaticSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PROBE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.parents = {
            child: parent
            for parent in ast.walk(cls.tree)
            for child in ast.iter_child_nodes(parent)
        }

    @classmethod
    def enclosing_function(cls, node: ast.AST) -> str | None:
        current = node
        while current in cls.parents:
            current = cls.parents[current]
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return current.name
        return None

    def test_probe_has_no_network_capable_imports(self) -> None:
        roots = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        self.assertEqual(set(), roots & FORBIDDEN_IMPORTS)

    def test_owned_child_lifecycle_calls_exist_only_in_run_command(self) -> None:
        violations = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node)
            if name in FORBIDDEN_CALLS:
                violations.append(name)
            if (
                name in {"Popen", "kill", "killpg"}
                and self.enclosing_function(node) != "run_command"
            ):
                violations.append(
                    f"{name} outside run_command"
                )
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "system"
            ):
                violations.append("os.system")
            if name in {"run", "Popen"}:
                shell_true = any(
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in node.keywords
                )
                if shell_true:
                    violations.append(f"subprocess.{name}(shell=True)")
        self.assertEqual([], violations)

    def test_popen_is_bounded_sanitized_and_commands_are_read_only(self) -> None:
        violations = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            if call_name(node) == "run" and isinstance(node.func, ast.Attribute):
                violations.append("subprocess.run is not byte bounded")
            if call_name(node) == "Popen":
                keywords = {keyword.arg: keyword.value for keyword in node.keywords}
                for required in ("stdout", "stderr", "cwd", "env", "shell"):
                    if required not in keywords:
                        violations.append(f"Popen without {required}")
                shell = keywords.get("shell")
                if not (
                    isinstance(shell, ast.Constant)
                    and shell.value is False
                ):
                    violations.append("Popen shell is not explicitly false")
            command_text = " ".join(literal_strings(node)).lower()
            for fragment in DESTRUCTIVE_FRAGMENTS:
                if fragment in command_text:
                    violations.append(fragment)
            words = set(command_text.replace(";", " ").split())
            for command in PACKAGE_MANAGER_COMMANDS:
                if command in words:
                    violations.append(command)
        for constant in ("MAX_COMMAND_TIMEOUT_SECONDS", "MAX_COMMAND_OUTPUT_BYTES"):
            if constant not in self.source:
                violations.append(f"missing {constant}")
        self.assertEqual([], violations)

    def test_serialized_output_does_not_contain_sensitive_keys(self) -> None:
        output_keys = {
            key.value
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Dict)
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        self.assertEqual(set(), output_keys & SENSITIVE_OUTPUT_KEYS)

    def test_windows_trust_anchors_are_not_read_from_environment(self) -> None:
        forbidden = (
            'os.environ.get("SystemRoot")',
            'os.environ.get("WINDIR")',
            'os.environ.get("ProgramFiles")',
            'os.getenv("SystemRoot")',
            'os.getenv("WINDIR")',
            'os.getenv("ProgramFiles")',
        )
        for fragment in forbidden:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, self.source)

    def test_owned_process_identity_and_cleanup_ceiling_are_explicit(self) -> None:
        self.assertIn("start_new_session", self.source)
        self.assertIn("CREATE_NEW_PROCESS_GROUP", self.source)
        self.assertIn("os.killpg", self.source)
        self.assertIn("COMMAND_CLEANUP_GRACE_SECONDS", self.source)
        self.assertNotIn("reader.join", self.source)


if __name__ == "__main__":
    unittest.main()
