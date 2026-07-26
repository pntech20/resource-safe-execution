import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_TEST = (
    REPO_ROOT
    / "examples"
    / "owned-browser-lifecycle"
    / "with-owned-browser.test.cjs"
)


class OwnedBrowserExampleTests(unittest.TestCase):
    def test_node_lifecycle_contract_passes(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required to test the public lifecycle example")
        result = subprocess.run(
            [node, "--test", str(NODE_TEST)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Node lifecycle tests failed:\n{result.stdout}\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
