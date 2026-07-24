import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = (
    REPO_ROOT / "skills" / "resource-safe-execution" / "scripts" / "resource_probe.py"
)
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib", "socket", "ftplib", "smtplib"}
FORBIDDEN_CALLS = {"kill", "killpg", "terminate", "send_signal", "Popen"}
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

    def test_probe_has_no_network_capable_imports(self) -> None:
        roots = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        self.assertEqual(set(), roots & FORBIDDEN_IMPORTS)

    def test_probe_has_no_process_termination_or_shell_execution(self) -> None:
        violations = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node)
            if name in FORBIDDEN_CALLS:
                violations.append(name)
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "system"
            ):
                violations.append("os.system")
            if name == "run":
                shell_true = any(
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in node.keywords
                )
                if shell_true:
                    violations.append("subprocess.run(shell=True)")
        self.assertEqual([], violations)

    def test_subprocess_calls_are_timed_and_commands_are_read_only(self) -> None:
        violations = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            if call_name(node) == "run" and isinstance(node.func, ast.Attribute):
                if not any(keyword.arg == "timeout" for keyword in node.keywords):
                    violations.append("subprocess.run without timeout")
            command_text = " ".join(literal_strings(node)).lower()
            for fragment in DESTRUCTIVE_FRAGMENTS:
                if fragment in command_text:
                    violations.append(fragment)
            words = set(command_text.replace(";", " ").split())
            for command in PACKAGE_MANAGER_COMMANDS:
                if command in words:
                    violations.append(command)
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


if __name__ == "__main__":
    unittest.main()
