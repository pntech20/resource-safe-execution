# Growth Conversion Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repository into a fast, trustworthy install funnel and package the canonical skill for OpenAI and Claude distribution.

**Architecture:** Keep `skills/resource-safe-execution/` as the single canonical payload. Add thin, declarative plugin manifests around that folder, put the benefit/demo/install path above the README's detailed safety case, and enforce the distribution surface with standard-library tests.

**Tech Stack:** Markdown, JSON, YAML, Python 3.10+ standard library, GitHub repository metadata, OpenAI plugin manifest, Claude Code plugin marketplace manifest.

## Global Constraints

- The canonical skill remains `skills/resource-safe-execution/`; do not duplicate or fork its files.
- The skill runtime remains Python 3.10+ standard-library-only.
- The skill itself performs no network access, telemetry, package installation, privilege escalation, or unrelated process termination.
- Fast installation must disclose that `npx skills` is a third-party installer with its own anonymous, opt-out install telemetry.
- Keep the audited `v0.1.0` checksum-verification route adjacent to the fast route.
- Do not claim physical macOS/Linux or proprietary-client runtime evidence that has not been collected.
- Do not change the nine-file release payload or its hashes in this plan.
- Use tests first for every machine-verifiable repository contract.

---

## File structure

- Modify `README.md`: outcome-led first screen, fast/audited install paths, activation prompt, trust strip, and demo placeholder.
- Create `.codex-plugin/plugin.json`: OpenAI plugin wrapper pointing at the canonical `skills/` directory.
- Create `.claude-plugin/plugin.json`: Claude Code plugin metadata.
- Create `.claude-plugin/marketplace.json`: self-hosted Claude marketplace entry for this repository.
- Create `.github/ISSUE_TEMPLATE/bug_report.yml`: structured defect intake.
- Create `.github/ISSUE_TEMPLATE/compatibility_report.yml`: runtime-evidence intake.
- Create `.github/ISSUE_TEMPLATE/config.yml`: private security-report routing.
- Create `CODE_OF_CONDUCT.md`: contributor conduct contract.
- Create `tests/test_growth_surface.py`: README and plugin-manifest contract tests.

### Task 1: Lock the README conversion contract

**Files:**
- Create: `tests/test_growth_surface.py`
- Test: `tests/test_growth_surface.py`

**Interfaces:**
- Consumes: repository root and existing `README.md`.
- Produces: `GrowthSurfaceTests`, which later tasks extend for plugin manifests.

- [ ] **Step 1: Create the failing README contract test**

```python
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
FAST_INSTALL = (
    "npx --yes skills@1.5.20 add pntech20/resource-safe-execution "
    "--skill resource-safe-execution --copy"
)


class GrowthSurfaceTests(unittest.TestCase):
    def test_readme_first_screen_is_outcome_led(self):
        text = README.read_text(encoding="utf-8")
        first_screen = "\n".join(text.splitlines()[:65])
        self.assertIn(
            "Let your AI agent run heavy jobs—without freezing your workstation.",
            first_screen,
        )
        self.assertIn(FAST_INSTALL, first_screen.replace("`\\\n", " "))
        self.assertIn("No telemetry", first_screen)
        self.assertIn("Watch the 30-second proof", first_screen)

    def test_readme_discloses_installer_telemetry_boundary(self):
        text = README.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(
                r"skills CLI.*anonymous.*install telemetry.*"
                r"Resource Safe Execution.*no telemetry",
                re.IGNORECASE | re.DOTALL,
            ),
        )

    def test_readme_keeps_audited_release_route(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn(
            "https://github.com/pntech20/resource-safe-execution/"
            "tree/v0.1.0/skills/resource-safe-execution",
            text,
        )
        self.assertIn("skill-manifest.json", text)
        self.assertIn("SHA256SUMS", text)
```

- [ ] **Step 2: Run the focused test and verify the expected failure**

Run:

```powershell
python -m unittest tests.test_growth_surface -v
```

Expected: FAIL because the current README does not contain the outcome-led
headline, proof link, or one-line canonical install command in its first 65
lines.

- [ ] **Step 3: Confirm the test does not alter the canonical payload**

Run:

```powershell
git diff -- skills/resource-safe-execution skill-manifest.json SHA256SUMS
```

Expected: no output.

- [ ] **Step 4: Commit the failing contract**

```powershell
git add tests/test_growth_surface.py
git commit -m "test: define growth surface contract"
```

### Task 2: Rewrite the README's first screen

**Files:**
- Modify: `README.md`
- Test: `tests/test_growth_surface.py`

**Interfaces:**
- Consumes: `FAST_INSTALL` and assertions from Task 1.
- Produces: the canonical public install funnel used by every campaign asset.

- [ ] **Step 1: Replace the current opening through the install section**

Use this exact content before the existing detailed safety material:

````markdown
# Resource Safe Execution

## Let your AI agent run heavy jobs—without freezing your workstation.

Resource Safe Execution is a cross-platform Agent Skill that inspects CPU,
memory, disk, GPU visibility, and running processes; chooses bounded
concurrency; verifies acceleration instead of assuming it; and cleans up only
processes the agent started.

[**Watch the 30-second proof**](assets/launch/resource-safe-execution-demo.gif)
· [Read the safety model](#safety-guarantees)
· [See compatibility evidence](docs/compatibility.md)

> **No telemetry · No network access · Python standard library only ·
> SHA-256 release manifest · Windows/macOS/Linux CI**

### Fast install

The open `skills` CLI can install the canonical folder:

```powershell
npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy
```

The third-party `skills` CLI records anonymous, opt-out install telemetry used
by skills.sh. Resource Safe Execution itself sends no telemetry and performs no
network access.

After installation, try:

> Before running this build and eight browser workers, inspect my machine,
> choose a safe profile, track every process you launch, and clean up only your
> owned tree.

### Audited install

For a reviewed, release-pinned copy:

```powershell
npx --yes skills@1.5.20 add https://github.com/pntech20/resource-safe-execution/tree/v0.1.0/skills/resource-safe-execution --skill resource-safe-execution --copy
```

Before use, verify the nine copied paths against
[`skill-manifest.json`](skill-manifest.json) and [`SHA256SUMS`](SHA256SUMS).
The detailed manual-copy procedure and client destinations appear below.
````

Keep the existing `Why`, `What it does`, `Safety guarantees`, client destination
table, evidence, validation, contributing, and license content below this new
opening. Remove duplicate introductory or convenience-install prose.

- [ ] **Step 2: Keep claims evidence-bounded**

Verify the opening does not say that the skill:

- guarantees a fixed CPU percentage;
- proves an application is using a GPU merely because hardware is visible;
- has been physically tested on macOS/Linux;
- has been runtime-tested in Claude Code or Antigravity.

- [ ] **Step 3: Run the focused tests**

```powershell
python -m unittest tests.test_growth_surface -v
```

Expected: all README contract tests PASS.

- [ ] **Step 4: Run Markdown link and whitespace checks**

```powershell
git diff --check
python -m unittest tests.test_quality -v
```

Expected: no whitespace errors and all quality tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs: make install value clear above the fold"
```

### Task 3: Add OpenAI and Claude plugin packages

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Modify: `tests/test_growth_surface.py`
- Test: `tests/test_growth_surface.py`

**Interfaces:**
- Consumes: canonical `skills/resource-safe-execution/`.
- Produces: declarative wrappers that expose the same folder without copying it.

- [ ] **Step 1: Add failing manifest tests**

Append to `GrowthSurfaceTests`:

```python
    def test_openai_plugin_points_to_canonical_skills(self):
        path = ROOT / ".codex-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "resource-safe-execution")
        self.assertEqual(data["version"], "0.2.0")
        self.assertEqual(data["skills"], "./skills/")
        self.assertTrue((ROOT / data["skills"]).resolve().is_dir())

    def test_claude_plugin_metadata_is_complete(self):
        path = ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "resource-safe-execution")
        self.assertEqual(data["version"], "0.2.0")
        self.assertEqual(data["license"], "MIT")
        self.assertEqual(
            data["repository"],
            "https://github.com/pntech20/resource-safe-execution",
        )

    def test_claude_marketplace_uses_repository_root_plugin(self):
        path = ROOT / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "pntech20-agent-skills")
        self.assertEqual(data["owner"]["name"], "pntech20")
        self.assertEqual(len(data["plugins"]), 1)
        plugin = data["plugins"][0]
        self.assertEqual(plugin["name"], "resource-safe-execution")
        self.assertEqual(plugin["source"], "./")
        self.assertEqual(plugin["version"], "0.2.0")
```

- [ ] **Step 2: Run the focused test and verify failure**

```powershell
python -m unittest tests.test_growth_surface -v
```

Expected: ERROR with missing `.codex-plugin/plugin.json`.

- [ ] **Step 3: Create the OpenAI manifest**

```json
{
  "name": "resource-safe-execution",
  "version": "0.2.0",
  "description": "Safely plan and run resource-intensive agent workloads.",
  "skills": "./skills/"
}
```

- [ ] **Step 4: Create the Claude plugin manifest**

```json
{
  "name": "resource-safe-execution",
  "description": "Bounds concurrency, verifies GPU use, and cleans up only owned processes.",
  "version": "0.2.0",
  "author": {
    "name": "pntech20"
  },
  "repository": "https://github.com/pntech20/resource-safe-execution",
  "homepage": "https://github.com/pntech20/resource-safe-execution",
  "license": "MIT"
}
```

- [ ] **Step 5: Create the Claude marketplace**

```json
{
  "name": "pntech20-agent-skills",
  "owner": {
    "name": "pntech20"
  },
  "plugins": [
    {
      "name": "resource-safe-execution",
      "source": "./",
      "description": "Bounds concurrency, verifies GPU use, and cleans up only owned processes.",
      "version": "0.2.0",
      "author": {
        "name": "pntech20"
      },
      "homepage": "https://github.com/pntech20/resource-safe-execution",
      "repository": "https://github.com/pntech20/resource-safe-execution",
      "license": "MIT",
      "category": "development",
      "tags": [
        "agent-skills",
        "resource-management",
        "process-safety"
      ]
    }
  ]
}
```

- [ ] **Step 6: Run local contract tests**

```powershell
python -m unittest tests.test_growth_surface -v
```

Expected: all tests PASS.

- [ ] **Step 7: Run official validators when installed**

```powershell
claude plugin validate .
```

Expected: valid marketplace and plugin. If Claude CLI is absent, record that
exact environment limit and keep the local JSON contract green; do not claim
official validation.

For OpenAI, run the current validator required by the plugin packaging docs.
Record the command and output in `docs/compatibility.md`; do not substitute the
Agent Skill validator for the plugin validator.

- [ ] **Step 8: Commit**

```powershell
git add .codex-plugin .claude-plugin tests/test_growth_surface.py
git commit -m "feat: package skill for OpenAI and Claude"
```

### Task 4: Add contribution intake surfaces

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/compatibility_report.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `CODE_OF_CONDUCT.md`

**Interfaces:**
- Consumes: `SECURITY.md`, `docs/compatibility.md`, repository URL.
- Produces: structured public issue intake while keeping vulnerabilities private.

- [ ] **Step 1: Create the bug form**

Use these required fields:

```yaml
name: Bug report
description: Report reproducible incorrect or unsafe behavior
title: "[Bug]: "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: "Do not report vulnerabilities here. Follow SECURITY.md."
  - type: input
    id: version
    attributes:
      label: Release or commit
      placeholder: "v0.2.0 or full commit SHA"
    validations:
      required: true
  - type: dropdown
    id: platform
    attributes:
      label: Operating system
      options: [Windows, macOS, Linux, Other]
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Minimal reproduction
      description: Remove command lines, usernames, tokens, and private paths.
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: Actual behavior
    validations:
      required: true
  - type: checkboxes
    id: privacy
    attributes:
      label: Privacy check
      options:
        - label: I removed credentials, command lines, usernames, and private data.
          required: true
```

- [ ] **Step 2: Create the compatibility form**

Required fields: release/commit, agent client and version, OS/version, install
method, real task, observed activation, probe result, cleanup result, and a
privacy confirmation. State that submission is evidence, not automatic support.

- [ ] **Step 3: Route security reports privately**

Create:

```yaml
blank_issues_enabled: false
contact_links:
  - name: Security vulnerability
    url: https://github.com/pntech20/resource-safe-execution/security/advisories/new
    about: Report vulnerabilities privately
```

- [ ] **Step 4: Add Contributor Covenant 2.1**

Create `CODE_OF_CONDUCT.md` from the unmodified Contributor Covenant 2.1
template. Set enforcement contact to the repository's private security/contact
route rather than inventing an email address.

- [ ] **Step 5: Validate YAML and repository links**

```powershell
python -c "import pathlib, yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('.github/ISSUE_TEMPLATE').glob('*.yml')]"
```

If PyYAML is unavailable, validate the forms by opening GitHub's new-issue page
after push; do not add PyYAML as a runtime dependency solely for this check.

- [ ] **Step 6: Commit**

```powershell
git add .github/ISSUE_TEMPLATE CODE_OF_CONDUCT.md
git commit -m "chore: add community issue intake"
```

### Task 5: Run the conversion-foundation completion gate

**Files:**
- Modify: `docs/compatibility.md` only if new runtime evidence was actually collected.
- Test: `tests/test_growth_surface.py`
- Test: existing `tests/`

**Interfaces:**
- Consumes: all outputs from Tasks 1–4.
- Produces: one green, reviewable foundation ready for launch assets.

- [ ] **Step 1: Run the complete repository suite**

```powershell
python -m compileall -q skills tests
python -m unittest discover -s tests
python tests/validate_skill.py skills/resource-safe-execution
python C:\Users\Admin\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/resource-safe-execution
```

Expected: all tests and both skill validators PASS.

- [ ] **Step 2: Verify the canonical payload is unchanged**

```powershell
python -m unittest tests.test_installation -v
git diff v0.1.0 -- skills/resource-safe-execution skill-manifest.json SHA256SUMS
```

Expected: installation tests PASS and no payload/hash diff.

- [ ] **Step 3: Verify repository hygiene**

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; only intentional uncommitted evidence notes, if
any, are listed.

- [ ] **Step 4: Commit evidence notes only when truthful**

```powershell
git add docs/compatibility.md
git commit -m "docs: record plugin validation evidence"
```

Skip this commit when no new runtime or official-validator evidence was
collected.

