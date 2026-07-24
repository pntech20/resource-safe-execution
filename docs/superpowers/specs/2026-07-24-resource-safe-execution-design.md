# Resource Safe Execution: Design Specification

Status: approved for implementation

Date: 2026-07-24

Repository: `pntech20/resource-safe-execution`

License: MIT

## 1. Purpose

Create a portable Agent Skill that helps AI coding agents make deliberate,
observable, and safe CPU, memory, disk, GPU, concurrency, rendering, and
process-lifecycle decisions.

The skill must prevent common agent failures such as:

- launching more heavy workers than an interactive machine can sustain;
- choosing CPU or software rendering when supported hardware acceleration is
  available;
- assuming that a detected GPU is usable by the selected framework;
- starting detached browsers, emulators, servers, or training jobs without
  retaining ownership information and a cleanup plan;
- terminating unrelated user processes by executable name;
- treating a brief utilization spike as proof that hardware is inadequate.

The skill provides guidance and read-only host inspection, with an explicit
optional output-file write. Version 1 does not enforce hard operating-system
quotas or terminate workload processes automatically.

## 2. Standards and portability contract

The canonical package will conform to the open Agent Skills specification.
It will live at:

```text
skills/resource-safe-execution/
```

Its `SKILL.md` will use the most portable frontmatter subset:

```yaml
---
name: resource-safe-execution
description: Use when planning, launching, monitoring, or cleaning up CPU-, memory-, disk-, GPU-, browser-, emulator-, or process-intensive work on Windows, macOS, or Linux.
---
```

The folder name and `name` value will match exactly. The name will remain
lowercase ASCII with single hyphens and below 64 characters. The description
will remain below 1,024 characters and state both the capability and its
activation conditions.

The shared `SKILL.md` will not depend on:

- experimental `allowed-tools`;
- Claude-only frontmatter, hooks, substitutions, or dynamic command syntax;
- Codex tool names, invocation syntax, plugin policy, or MCP metadata;
- Antigravity Rules, Workflows, Hooks, Sidecars, or plugin manifests;
- absolute installation paths or one shell's variable syntax.

Instructions will be imperative, use relative resource paths, define explicit
inputs and outputs, and keep the main document below 500 lines and 5,000
tokens. Optional `agents/openai.yaml` metadata may enhance Codex presentation,
but the skill must work identically without it.

## 3. Compatibility levels

Compatibility claims will distinguish format, installation, and runtime
behavior.

### Tier 1: portable targets

- OpenAI Codex
- Claude Code
- Google Antigravity IDE

Each Tier 1 client will receive:

1. Agent Skills contract validation.
2. A clean-directory installation smoke test.
3. Documented project and personal installation paths from primary sources.
4. Shared behavior-evaluation scenarios that do not require vendor-only syntax.

Actual client-runtime results will be recorded separately with the client
version, operating system, installation method, and test date. A release will
not imply that an unavailable proprietary client was exercised.

### Tier 2: format and installation evaluated

- Cursor
- OpenCode
- GitHub Copilot
- Other clients supported by the open `skills` installer

Tier 2 means the same canonical package installs without modification. It does
not claim that every client has completed the behavioral evaluation suite.

Antigravity CLI variants that require a flat Markdown file rather than a
directory containing `SKILL.md` will be documented as adapters. Generated
adapters must derive from the canonical instructions; independently maintained
copies are prohibited.

## 4. Repository architecture

```text
resource-safe-execution/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   └── superpowers/
│       └── specs/
├── skills/
│   └── resource-safe-execution/
│       ├── SKILL.md
│       ├── agents/
│       │   └── openai.yaml
│       ├── evals/
│       │   └── evals.json
│       ├── references/
│       │   ├── gpu-selection.md
│       │   ├── linux.md
│       │   ├── macos.md
│       │   ├── process-lifecycle.md
│       │   └── windows.md
│       └── scripts/
│           └── resource_probe.py
├── tests/
│   ├── fixtures/
│   ├── test_contract.py
│   ├── test_installation.py
│   ├── test_probe.py
│   └── test_safety.py
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── SECURITY.md
```

Repository documentation, CI configuration, development tests, and fixtures
stay outside the installed skill folder. Installing the skill therefore copies
only the instructions, references, evaluations, and runtime probe.

## 5. Resource probe

`resource_probe.py` will be a Python 3.10+ standard-library program. It will
perform read-only host inspection and require no package installation, network
access, administrator privileges, telemetry, or persistent service. Its
optional output-file write creates a new regular file exclusively and refuses
existing destinations, symlinks, and invalid parent paths.

### Inputs

- output mode: concise text or JSON;
- sampling duration within a bounded range;
- optional output file, created exclusively without an overwrite mode;
- optional inclusion of a privacy-preserving top-process summary.

### Output

The stable JSON document will contain:

- schema and probe versions;
- timestamp, platform, architecture, and power context when available;
- logical CPU count, sampled utilization, and load information;
- total and available memory;
- working-volume disk capacity and free space;
- detected graphics devices and available compute/rendering backends;
- NVIDIA driver, VRAM, and utilization data when `nvidia-smi` is available;
- Apple Silicon or Intel/AMD graphics information on macOS;
- top process PID, name, CPU, and memory only when requested;
- warnings, unavailable metrics, and the exact reason each metric is absent;
- conservative concurrency and headroom recommendations.

The process summary must not emit command lines, environment variables,
usernames, file contents, access tokens, or network destinations.

### Platform adapters

- Windows: use documented PowerShell/CIM and NVIDIA interfaces with trusted
  absolute executable paths, five-second subprocess timeouts, a one-MiB
  combined-output bound, and locale-tolerant parsing.
- macOS: use `sysctl`, `vm_stat`, `ps`, `df`, `pmset`, and
  `system_profiler -json` when available. Treat Apple Silicon memory as shared
  rather than adding CPU and GPU memory together.
- Linux: use `/proc`, `ps`, `df`, and `nvidia-smi` when available.

Missing or restricted commands will degrade individual metrics, not fail the
entire probe. An unsupported platform returns a clear nonzero exit status and
does not guess.

## 6. Agent workflow

When activated, the skill will require this sequence:

1. Run the read-only preflight probe before a computationally heavy or
   long-lived action.
2. Classify the workload as latency-sensitive, throughput-oriented,
   memory-bound, GPU-suitable, browser/rendering, emulator, or unknown.
3. Choose a balanced, low-impact, or throughput resource profile based on the
   user's goal and whether the machine is interactive.
4. Verify that the chosen framework or application can actually use the
   detected acceleration backend.
5. Define process ownership and teardown before launching long-lived work.
6. Sample utilization after startup and compare it with the stated workload
   expectation.
7. Adjust concurrency or rendering only from observed evidence.
8. Terminate only processes owned by the task, then run a postflight snapshot
   when cleanup or performance is material.

High utilization is not automatically an error. It becomes actionable when it
is unexpected, sustained, makes the machine unusable, causes thermal or memory
pressure, or contradicts the selected profile.

## 7. Rendering and GPU decisions

The skill will separate device detection from successful acceleration.

Agents must verify the active backend through the application or framework
when possible. A GPU listed by the operating system is insufficient evidence
that a browser, emulator, model, or numerical library is using it.

When a hardware renderer is verified and the workload has no demonstrated
compatibility failure, agents must not add software-rendering flags such as
SwiftShader, llvmpipe, forced WARP, `--disable-gpu`, or equivalent settings.

When a reproducible hardware-rendering test fails, the agent may use a
software renderer for that task. It must record the failing test, scope the
fallback to the owned process, reduce concurrency where appropriate, and
restore the normal configuration afterward.

GPU compute will be recommended only when the algorithm, data size, framework,
driver, memory capacity, and transfer costs support it. The skill will not
promise that arbitrary CPU work can move to a GPU.

## 8. Process ownership and cleanup

Before launching a long-lived process, an agent must retain:

- root PID;
- process start time or equivalent identity evidence;
- launch purpose;
- working directory;
- expected lifetime;
- cleanup command or API;
- whether the process created a child process group.

Broad termination by executable name is prohibited. Examples include
`taskkill /IM`, `Stop-Process -Name`, `killall`, and unscoped `pkill`.

Detached or unreferenced execution is permitted only when task requirements
need persistence and ownership information has already been recorded. A
process that must survive the agent session is reported to the user instead of
being silently abandoned.

Version 1 will teach and evaluate this discipline but will not ship an
automatic workload-process killer. The probe never terminates pre-existing or
unrelated processes. It may stop its own bounded diagnostic child only after a
timeout or output overflow. A later opt-in governor may add process-group
timeouts after separate security design and testing.

## 9. Testing strategy

### Deterministic tests

- Validate the portable frontmatter allowlist, name/path match, description
  length, line/token budget, relative references, and forbidden vendor syntax.
- Test Windows, macOS, and Linux parsers with fixtures covering normal,
  missing-tool, timeout, permission, malformed-output, localized, no-GPU, and
  multiple-GPU conditions.
- Test JSON schema stability, exit codes, sampling bounds, concurrency boundary
  values, and privacy redaction.
- Assert that diagnostic-child creation and termination exist only in the
  bounded command wrapper, which may stop only its own child on timeout or
  output overflow; prohibit every other process-termination path, download,
  telemetry, package-installation, or privilege-escalation behavior.
- Smoke-test repository discovery and installation into clean temporary agent
  homes for Codex, Claude Code, Antigravity, Cursor, and OpenCode.

### Agent behavior evaluations

Run baseline scenarios without the skill before writing its rules. Scenarios
will combine at least three pressures such as deadline, sunk cost, authority,
machine responsiveness, and a seemingly convenient software-rendering
fallback.

Repeat the same scenarios with the skill and evaluate whether agents:

- run a preflight check;
- preserve interactive headroom;
- verify actual acceleration rather than infer it;
- avoid unowned detached processes;
- refuse broad kill-by-name cleanup;
- distinguish intentional throughput from accidental overload;
- report unsupported or unverified conditions honestly.

New rationalizations discovered during evaluation will become explicit
counters and regression scenarios.

## 10. Continuous integration

GitHub Actions will run:

- contract and unit tests on Linux, Windows, and macOS;
- supported Python-version checks;
- style and static analysis;
- canonical-skill discovery;
- copy-based installer smoke tests for named agents;
- macOS Intel and Apple Silicon jobs when corresponding hosted runners are
  available to the repository.

Model-backed evaluations will not block ordinary pull requests because they
require credentials and can be nondeterministic. They will run manually or on
a controlled schedule and publish their configuration and scoring criteria.

Hosted runners prove operating-system compatibility, not physical consumer GPU
behavior. Release notes will identify which combinations were exercised on
physical Windows 11, Intel Mac, Apple Silicon Mac, NVIDIA, AMD, and integrated
graphics hardware.

## 11. Security and contribution model

The project will publish:

- a threat model and security-reporting path;
- a no-network and no-telemetry guarantee for the runtime probe;
- dependency review and pinned CI actions;
- contribution requirements for tests and compatibility claims;
- a rule that executable changes require focused review;
- provenance for generated adapters.

The README will warn that skills influence agent behavior and that developers
should review executable scripts before installation.

## 12. Distribution and versioning

The GitHub repository is the distribution source. Developers can install the
canonical skill through the open `skills` installer and select one or more
agent targets. Manual installation paths will also be documented from each
agent's primary documentation.

Releases will use semantic versioning:

- patch: guidance, detection, or parser fixes without contract changes;
- minor: backward-compatible metrics, platform support, or references;
- major: incompatible output schema or required workflow changes.

The JSON schema version and project release version will be independent so
documentation-only releases do not force data-format changes.

## 13. Acceptance criteria for version 1.0

Version 1.0 is ready only when:

1. The skill passes its contract validator and contains no required
   vendor-specific syntax.
2. The probe passes the full deterministic test suite on Windows, macOS, and
   Linux CI.
3. Clean installation smoke tests pass for Codex, Claude Code, and
   Antigravity; Tier 2 results are documented separately.
4. Baseline agent evaluations fail for the intended reasons, and the
   corresponding skill-enabled evaluations pass.
5. No probe path performs network access, telemetry, privilege escalation, or
   package installation. The probe never terminates pre-existing or unrelated
   processes and may stop only its own diagnostic child on timeout or output
   overflow.
6. The Windows probe runs successfully on the maintainer's machine.
7. macOS support is marked CI-validated until physical Intel and Apple Silicon
   results are available.
8. README, security, contribution, license, and release documentation match
   implemented behavior without placeholders or overstated claims.

## 14. Implementation order

1. Create baseline agent pressure scenarios and capture failures.
2. Write contract, probe, and safety tests that fail for missing behavior.
3. Implement the minimum portable skill and probe needed to pass.
4. Add platform references and agent installation documentation.
5. Run skill-enabled behavior evaluations and close observed loopholes.
6. Run the complete local validation suite.
7. Install the canonical folder locally and test Codex discovery.
8. Push implementation, enable CI, inspect every job, and prepare version
   `v1.0.0` only when all acceptance criteria are evidenced.
