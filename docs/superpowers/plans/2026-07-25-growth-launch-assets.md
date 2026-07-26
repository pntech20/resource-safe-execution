# Growth Launch Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an evidence-bounded social preview, 30–45 second demo, three short case studies, and reusable launch copy that all drive to the canonical install command.

**Architecture:** Derive every claim from existing evaluation artifacts and the live probe. Keep source/storyboard files separate from rendered binaries, validate asset dimensions and README references mechanically, and reserve account-specific publishing for the account holder.

**Tech Stack:** Markdown, PNG, animated GIF or MP4, Python 3.10+ standard library for validation, existing evaluation artifacts, optional local media tooling for rendering only.

## Global Constraints

- Use real probe/evaluation behavior; do not fabricate a client UI or benchmark.
- Never show command lines, usernames, tokens, private paths, environment variables, or unrelated processes.
- Do not claim a guaranteed CPU percentage or automatic GPU acceleration.
- The social preview must be 1280×640 PNG, solid-background, and under 1 MiB.
- The README demo must be 30–45 seconds, legible on mobile, and under 10 MiB if committed as GIF.
- All assets use the same headline and canonical install command as the growth design.
- Do not add media or rendering dependencies to the skill runtime.

---

## File structure

- Create `docs/launch/demo-storyboard.md`: exact scenes, timings, source evidence, and redaction checklist.
- Create `assets/launch/social-preview-source.svg`: editable source for the social card.
- Create `assets/launch/resource-safe-execution-social-preview.png`: upload-ready social card.
- Create `assets/launch/resource-safe-execution-demo.gif`: README proof asset.
- Create `docs/case-studies/concurrency.md`: bounded-worker case study.
- Create `docs/case-studies/gpu-verification.md`: hardware-versus-backend case study.
- Create `docs/case-studies/process-cleanup.md`: ownership-safe cleanup case study.
- Create `docs/launch/campaign-copy.md`: channel-specific, authorship-disclosed drafts.
- Create `tests/test_launch_assets.py`: binary dimensions, size, references, and claim-boundary checks.

### Task 1: Define asset contracts and storyboard

**Files:**
- Create: `tests/test_launch_assets.py`
- Create: `docs/launch/demo-storyboard.md`
- Test: `tests/test_launch_assets.py`

**Interfaces:**
- Consumes: `README.md`, evaluation files under `docs/evaluations/`.
- Produces: binary asset contracts and the exact demo narrative.

- [ ] **Step 1: Write failing asset tests**

```python
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "assets/launch/resource-safe-execution-social-preview.png"
DEMO = ROOT / "assets/launch/resource-safe-execution-demo.gif"


def png_dimensions(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("not a PNG")
    return struct.unpack(">II", data[16:24])


class LaunchAssetTests(unittest.TestCase):
    def test_social_preview_contract(self):
        self.assertEqual(png_dimensions(PREVIEW), (1280, 640))
        self.assertLess(PREVIEW.stat().st_size, 1_000_000)

    def test_demo_contract(self):
        data = DEMO.read_bytes()
        self.assertIn(data[:6], (b"GIF87a", b"GIF89a"))
        self.assertLess(DEMO.stat().st_size, 10_000_000)

    def test_readme_references_committed_demo(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "assets/launch/resource-safe-execution-demo.gif",
            text,
        )

    def test_campaign_assets_avoid_unproven_claims(self):
        paths = [
            ROOT / "docs/launch/demo-storyboard.md",
            ROOT / "docs/launch/campaign-copy.md",
            ROOT / "docs/case-studies/concurrency.md",
            ROOT / "docs/case-studies/gpu-verification.md",
            ROOT / "docs/case-studies/process-cleanup.md",
        ]
        joined = "\n".join(
            path.read_text(encoding="utf-8") for path in paths if path.exists()
        ).lower()
        for forbidden in (
            "guarantees cpu",
            "always uses the gpu",
            "physically tested on macos",
            "physically tested on linux",
        ):
            self.assertNotIn(forbidden, joined)
```

- [ ] **Step 2: Run tests and verify missing-asset failure**

```powershell
python -m unittest tests.test_launch_assets -v
```

Expected: ERROR because the PNG and GIF do not exist.

- [ ] **Step 3: Write the exact storyboard**

Use this timeline:

```markdown
# 38-second demo storyboard

## 0–4s — Pain
Prompt: "Run this build with eight browser workers, use the GPU, then clean up."
Caption: "Agents guess. Your workstation pays."

## 4–10s — Read-only preflight
Show only redacted totals for CPU, memory, disk, and GPU visibility.
Caption: "Inspect before launching."

## 10–17s — Bounded plan
Show the skill selecting three balanced workers instead of eight.
Caption: "Bound concurrency from current headroom."

## 17–23s — Verify acceleration
Show: "GPU visible" followed by "backend use must still be verified."
Caption: "Hardware detected ≠ workload accelerated."

## 23–31s — Track ownership
Show an owned PID set and a refusal to terminate by broad process name.
Caption: "Track what the agent starts."

## 31–36s — Cleanup
Show only the owned process tree being stopped.
Caption: "Clean up only owned work."

## 36–38s — CTA
Show: `npx skills add pntech20/resource-safe-execution`
Caption: "No network. No telemetry. Standard library only."
```

For every scene, link the exact source evaluation file and line/section used.
Include a pre-capture checklist that closes unrelated apps and verifies no
private information is visible.

- [ ] **Step 4: Commit the contract and storyboard**

```powershell
git add tests/test_launch_assets.py docs/launch/demo-storyboard.md
git commit -m "test: define launch asset contracts"
```

### Task 2: Create the social preview

**Files:**
- Create: `assets/launch/social-preview-source.svg`
- Create: `assets/launch/resource-safe-execution-social-preview.png`
- Test: `tests/test_launch_assets.py`

**Interfaces:**
- Consumes: approved headline, trust strip, repository name.
- Produces: editable source and 1280×640 upload artifact.

- [ ] **Step 1: Create the editable source**

The composition is:

- solid near-black background;
- small eyebrow: `RESOURCE SAFE EXECUTION`;
- large two-line headline: `Heavy agent jobs.` / `Responsive workstation.`;
- supporting line: `Bound concurrency · Verify GPU use · Own process cleanup`;
- bottom-left: `Agent Skill · Windows · macOS · Linux`;
- bottom-right: `github.com/pntech20/resource-safe-execution`;
- no vendor logos or implied endorsements.

Use high-contrast white text, one cyan accent, and a minimum rendered text size
of 30 px.

- [ ] **Step 2: Render the PNG**

Use an available deterministic SVG renderer. Example when ImageMagick is
installed:

```powershell
magick -background none assets/launch/social-preview-source.svg assets/launch/resource-safe-execution-social-preview.png
```

If ImageMagick is unavailable, use the workspace's browser screenshot tooling
at exactly 1280×640. Do not rasterize with an online service.

- [ ] **Step 3: Validate**

```powershell
python -m unittest tests.test_launch_assets.LaunchAssetTests.test_social_preview_contract -v
```

Expected: PASS.

- [ ] **Step 4: Visually inspect at full size and 640×320**

Verify no text clips, the URL remains readable, and the card is understandable
without the README.

- [ ] **Step 5: Commit**

```powershell
git add assets/launch/social-preview-source.svg assets/launch/resource-safe-execution-social-preview.png
git commit -m "docs: add repository social preview"
```

### Task 3: Produce the 30–45 second proof

**Files:**
- Create: `assets/launch/resource-safe-execution-demo.gif`
- Test: `tests/test_launch_assets.py`

**Interfaces:**
- Consumes: `docs/launch/demo-storyboard.md` and the cited evaluation evidence.
- Produces: the README's primary proof asset.

- [ ] **Step 1: Prepare a clean capture environment**

- Set terminal font to at least 22 px.
- Use a 16:9 capture area at 1200×675 or larger.
- Hide username, working path, clock, notifications, tabs, and unrelated
  processes.
- Re-run the cited probe/evaluation commands immediately before capture.

- [ ] **Step 2: Capture one continuous screen-only take**

Follow the storyboard timings. Do not splice output from different operating
systems into a single implied run. If live timing is unreliable, use a
deterministic terminal playback generated from the freshly captured redacted
transcript and label it `Recorded evaluation playback`.

- [ ] **Step 3: Encode the GIF**

With ffmpeg:

```powershell
ffmpeg -i resource-safe-execution-demo-source.mp4 -vf "fps=10,scale=1200:-2:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" -loop 0 assets/launch/resource-safe-execution-demo.gif
```

If the result exceeds 10 MiB, reduce to 8 fps, then 960 px width. Do not shorten
below 30 seconds or make terminal text unreadable.

- [ ] **Step 4: Validate and visually inspect**

```powershell
python -m unittest tests.test_launch_assets.LaunchAssetTests.test_demo_contract -v
```

Expected: PASS. Watch the loop twice at desktop width and once at 360 px.

- [ ] **Step 5: Commit**

```powershell
git add assets/launch/resource-safe-execution-demo.gif
git commit -m "docs: add 38-second execution safety demo"
```

### Task 4: Publish three evidence-backed case studies

**Files:**
- Create: `docs/case-studies/concurrency.md`
- Create: `docs/case-studies/gpu-verification.md`
- Create: `docs/case-studies/process-cleanup.md`
- Test: `tests/test_launch_assets.py`

**Interfaces:**
- Consumes: baseline and skill-enabled evaluation artifacts.
- Produces: short proof pages used by community posts.

- [ ] **Step 1: Write each case study with one shared structure**

```markdown
# [Outcome-led title]

## The risky request
[The original task, with sensitive details removed.]

## What an unbounded agent may assume
[Observed baseline behavior, linked to raw evidence.]

## What the skill changes
[Observed skill-enabled behavior, linked to raw evidence.]

## What it does not prove
[Exact limitation.]

## Try it
`npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy`
```

- [ ] **Step 2: Use these outcome titles**

- `Bound parallelism from current headroom—not a guessed worker count`
- `A visible GPU is not proof that the workload uses it`
- `Stop the process tree you own—not every process with the same name`

- [ ] **Step 3: Verify every behavioral statement has a repository evidence link**

No percentages or performance improvements may be introduced unless the
linked evaluation records them.

- [ ] **Step 4: Run claim-boundary tests**

```powershell
python -m unittest tests.test_launch_assets -v
```

Expected: all current tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add docs/case-studies
git commit -m "docs: publish resource safety case studies"
```

### Task 5: Prepare channel-specific campaign copy

**Files:**
- Create: `docs/launch/campaign-copy.md`
- Test: `tests/test_launch_assets.py`

**Interfaces:**
- Consumes: demo, case studies, canonical install command, community constraints.
- Produces: drafts; it does not publish them.

- [ ] **Step 1: Write the maker disclosure**

Use this sentence wherever authorship disclosure is appropriate:

> I built Resource Safe Execution after my own workstation became unusable
> while agents, emulators, and browser workers competed for resources.

- [ ] **Step 2: Write exact drafts for five surfaces**

Use these drafts as the source text, then make only rule-required edits:

**X**

```text
My AI agents kept freezing my workstation. Resource Safe Execution checks
headroom, bounds concurrency, verifies GPU use, and cleans up only owned
processes. Local, no telemetry. Demo + install:
https://github.com/pntech20/resource-safe-execution
```

**LinkedIn**

```text
I built Resource Safe Execution after my workstation became unusable while
agents, emulators, and browser workers competed for resources.

It is an open Agent Skill for Codex, Claude Code, Antigravity, and other
compatible clients. Before heavy work, it checks CPU, memory, disk, GPU
visibility, and process pressure. It then chooses bounded concurrency, requires
GPU acceleration to be verified, tracks the processes it starts, and cleans up
only that owned tree.

The runtime uses only Python's standard library. It makes no network calls and
sends no telemetry.

The 38-second demo, safety model, tests, and install command are here:
https://github.com/pntech20/resource-safe-execution
```

**Show HN title**

```text
Show HN: Resource Safe Execution – stop AI agents freezing your workstation
```

**Show HN maker comment**

```text
I built this after running coding agents, Android emulators, browser workers,
and local builds on the same Windows workstation. The common failure was not
one bad tool; it was every tool assuming it could use all available resources.

Resource Safe Execution is an Agent Skills-compatible workflow plus a
read-only Python probe. It asks the agent to inspect current headroom, choose a
bounded worker profile, distinguish visible GPU hardware from verified backend
use, record owned PIDs, and refuse broad name-based cleanup.

The probe uses the standard library, has no network or telemetry, and does not
terminate pre-existing processes. The repository includes 127 tests, a
six-job Windows/macOS/Linux CI matrix, checksums, and explicit evidence limits.

Install:
npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy

I would especially value feedback on: (1) where the activation description is
too broad or too narrow, (2) workloads where the conservative profile is still
too aggressive, and (3) client/OS combinations you can test on real hardware.
```

**Reddit base body**

```text
Disclosure: I am the maintainer.

My workstation became unresponsive when coding agents, emulators, browser
workers, and builds all guessed their own parallelism. I made an open-source
Agent Skill that runs a read-only preflight, chooses bounded concurrency,
separates GPU visibility from verified acceleration, and cleans up only the
process tree the agent started.

It uses the Python standard library, makes no network calls, and sends no
telemetry. The repository includes the raw evaluation cases and does not claim
physical macOS/Linux or every client runtime has been tested.

Demo, source, and install:
https://github.com/pntech20/resource-safe-execution

I am looking for concrete feedback on activation accuracy and real workloads,
not votes or stars.
```

Create separate `r/ClaudeAI`, `r/ClaudeCode`, `r/codex`, and `r/opensource`
subsections. In each subsection, copy the current rule URL and permitted flair
verbatim above the base body. Delete a subsection rather than publishing it if
the account or project is ineligible on launch day.

No draft asks for upvotes, stars, reposts, or coordinated engagement.

- [ ] **Step 3: Add a publishing checklist**

Before each post: re-read current community rules, disclose authorship, verify
the install command, upload native media, remove tracking parameters, and remain
available for replies.

- [ ] **Step 4: Run claim-boundary tests**

```powershell
python -m unittest tests.test_launch_assets -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add docs/launch/campaign-copy.md
git commit -m "docs: prepare ethical launch copy"
```

### Task 6: Run the launch-asset completion gate

**Files:**
- Test: `tests/test_launch_assets.py`
- Test: existing `tests/`

**Interfaces:**
- Consumes: all asset-plan outputs.
- Produces: a visually inspected, mechanically validated launch bundle.

- [ ] **Step 1: Run focused and full tests**

```powershell
python -m unittest tests.test_launch_assets -v
python -m unittest discover -s tests
```

Expected: all tests PASS.

- [ ] **Step 2: Verify binaries and README references**

```powershell
Get-Item assets/launch/resource-safe-execution-social-preview.png, assets/launch/resource-safe-execution-demo.gif | Select-Object Name,Length
git grep -n "resource-safe-execution-demo.gif"
```

Expected: PNG under 1 MiB, GIF under 10 MiB, and the README contains the demo
reference.

- [ ] **Step 3: Review every visual against the redaction checklist**

Use original-resolution inspection. Confirm no private paths, usernames,
notifications, unrelated process names, tokens, or unsupported claims appear.

- [ ] **Step 4: Verify repository hygiene**

```powershell
git diff --check
git status --short
```

Expected: clean after all task commits.
