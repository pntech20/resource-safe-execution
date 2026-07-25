import re
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "launch"
PREVIEW = ASSET_DIR / "resource-safe-execution-social-preview.png"
PREVIEW_SOURCE = ASSET_DIR / "social-preview-source.svg"
DEMO = ASSET_DIR / "resource-safe-execution-demo.gif"
STORYBOARD = ROOT / "docs" / "launch" / "demo-storyboard.md"
CASE_STUDIES = {
    "concurrency.md": (
        "Bound parallelism from current headroom—not a guessed worker count",
        "../evaluations/raw/concurrency-pressure.md",
        "../evaluations/raw/skill-enabled/concurrency-pressure.md",
    ),
    "gpu-verification.md": (
        "A visible GPU is not proof that the workload uses it",
        "../evaluations/raw/gpu-assumption.md",
        "../evaluations/raw/skill-enabled/gpu-assumption.md",
    ),
    "process-cleanup.md": (
        "Stop the process tree you own—not every process with the same name",
        "../evaluations/raw/cleanup-pressure.md",
        "../evaluations/raw/skill-enabled/cleanup-pressure.md",
    ),
}
CANONICAL_INSTALL = (
    "npx --yes skills@1.5.20 add pntech20/resource-safe-execution "
    "--skill resource-safe-execution --copy"
)


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("not a PNG")
    return struct.unpack(">II", data[16:24])


def gif_contract(path: Path) -> tuple[tuple[int, int], float]:
    data = path.read_bytes()
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        raise AssertionError("not a GIF")
    width, height = struct.unpack("<HH", data[6:10])
    delays = [
        struct.unpack("<H", match.group(1))[0]
        for match in re.finditer(
            rb"\x21\xf9\x04.([\x00-\xff]{2}).\x00",
            data,
            flags=re.DOTALL,
        )
    ]
    if not delays:
        raise AssertionError("GIF has no frame delays")
    return (width, height), sum(delays) / 100


class LaunchAssetTests(unittest.TestCase):
    def test_social_preview_contract(self):
        self.assertEqual(png_dimensions(PREVIEW), (1280, 640))
        self.assertIn(PREVIEW.read_bytes()[25], (2, 3))
        self.assertLess(PREVIEW.stat().st_size, 1_000_000)

    def test_social_preview_source_has_exact_copy_and_legible_type(self):
        source = PREVIEW_SOURCE.read_text(encoding="utf-8")
        for text in (
            "RESOURCE SAFE EXECUTION",
            "Heavy agent jobs.",
            "Responsive workstation.",
            "Bound concurrency · Verify GPU use · Own process cleanup",
            "Agent Skill · Windows · macOS · Linux",
            "github.com/pntech20/resource-safe-execution",
        ):
            self.assertIn(text, source)
        sizes = [int(value) for value in re.findall(r"font-size=\"(\d+)", source)]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 30)

    def test_demo_contract(self):
        dimensions, duration = gif_contract(DEMO)
        self.assertGreaterEqual(dimensions[0], 960)
        self.assertGreaterEqual(dimensions[1], 540)
        self.assertGreaterEqual(duration, 30)
        self.assertLessEqual(duration, 45)
        self.assertLess(DEMO.stat().st_size, 10_000_000)

    def test_readme_references_committed_demo(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "assets/launch/resource-safe-execution-demo.gif",
            text,
        )

    def test_storyboard_records_evidence_and_claim_boundaries(self):
        text = STORYBOARD.read_text(encoding="utf-8")
        self.assertIn("RECORDED EVALUATION PLAYBACK", text)
        self.assertIn(CANONICAL_INSTALL, text)
        self.assertIn("skills CLI", text)
        self.assertIn("anonymous, opt-out install telemetry", text)
        self.assertIn(
            "docs/evaluations/raw/skill-enabled/concurrency-pressure.md",
            text,
        )
        self.assertIn(
            "docs/evaluations/2026-07-24-skill-enabled.md",
            text,
        )
        self.assertNotIn("selects three", text.lower())
        self.assertNotIn("no telemetry. no network.", text.lower())

    def test_case_studies_have_shared_structure_and_evidence(self):
        section_names = (
            "## The risky request",
            "## What an unbounded agent may assume",
            "## What the skill changes",
            "## What it does not prove",
            "## Try it",
        )
        for filename, (title, baseline_link, skill_link) in CASE_STUDIES.items():
            with self.subTest(filename=filename):
                text = (
                    ROOT / "docs" / "case-studies" / filename
                ).read_text(encoding="utf-8")
                self.assertEqual(text.splitlines()[0], f"# {title}")
                for section_name in section_names:
                    self.assertEqual(text.count(section_name), 1)
                self.assertIn(CANONICAL_INSTALL, text)
                self.assertIn(f"]({baseline_link})", text)
                self.assertIn(f"]({skill_link})", text)
                self.assertIn(
                    "](../evaluations/2026-07-24-skill-enabled.md",
                    text,
                )
                self.assertIn(
                    "not an evaluation of the current `SKILL.md`",
                    text,
                )
                self.assertNotRegex(text, r"\b\d+(?:\.\d+)?%")
                self.assertNotRegex(
                    text.lower(),
                    r"\b(?:\d+|one|two|three|four|five|six|seven|eight)"
                    r"[ -]+(?:playwright[ -]+)?workers?\b",
                )
                for unsupported in (
                    "physically tested",
                    "performance improvement",
                    "runtime improvement",
                    "speedup",
                    "validated in current clients",
                ):
                    self.assertNotIn(unsupported, text.lower())

    def test_campaign_assets_avoid_unproven_claims(self):
        paths = [
            STORYBOARD,
            ROOT / "docs" / "launch" / "campaign-copy.md",
            ROOT / "docs" / "case-studies" / "concurrency.md",
            ROOT / "docs" / "case-studies" / "gpu-verification.md",
            ROOT / "docs" / "case-studies" / "process-cleanup.md",
        ]
        joined = "\n".join(
            path.read_text(encoding="utf-8") for path in paths if path.exists()
        ).lower()
        for forbidden in (
            "guarantees cpu",
            "always uses the gpu",
            "physically tested on macos",
            "physically tested on linux",
            "fixed three-worker",
        ):
            self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main()
