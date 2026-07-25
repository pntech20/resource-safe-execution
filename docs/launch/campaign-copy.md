# Campaign copy drafts

These are manual-posting drafts, not publication instructions. They do not ask
for votes, stars, reposts, or other artificial engagement.

Rules checked: 2026-07-25

## Shared facts and disclosure

I built Resource Safe Execution after my own workstation became unusable while
agents, emulators, and browser workers competed for resources.

Resource Safe Execution is a free, MIT-licensed agent skill that derives
concurrency from current headroom, verifies GPU use, and cleans up only the
process tree the agent owns. The project has 140+ tests.

The skill runtime sends no telemetry and makes no network calls. The third-party
`skills` CLI records anonymous, opt-out install telemetry.

Canonical pinned install:

```sh
npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy
```

Evidence: [38-second demo](../../assets/launch/resource-safe-execution-demo.gif),
[concurrency case study](../case-studies/concurrency.md),
[GPU verification case study](../case-studies/gpu-verification.md), and
[process-cleanup case study](../case-studies/process-cleanup.md).

## X

```text
AI agents froze my PC. I built Resource Safe Execution: an open skill that bounds concurrency, verifies GPU use, and cleans only owned processes. Runtime: no network calls or telemetry. 38s demo: https://github.com/pntech20/resource-safe-execution
```

## LinkedIn

```text
I built Resource Safe Execution after my own workstation became unusable while agents, emulators, and browser workers competed for resources.

It gives coding agents a repeatable safety workflow: inspect current headroom, choose a conservative concurrency bound, verify real GPU use, and clean up only the process tree they own. The project is MIT-licensed and has 140+ tests.

The package is formatted for Codex, Claude Code, and Antigravity; the documented compatibility matrix distinguishes packaging support from runtime validation. The skill runtime sends no telemetry and makes no network calls. The third-party skills CLI records anonymous, opt-out install telemetry.

Demo, evidence, and pinned install command:
https://github.com/pntech20/resource-safe-execution
```

## Show HN

Title: `Show HN: Resource Safe Execution – keep heavy local agent jobs within headroom`

Maker comment:

```text
I built Resource Safe Execution after my own workstation became unusable while agents, emulators, and browser workers competed for resources.

The skill guides an agent through inspecting current resources, deriving a conservative concurrency bound, verifying GPU use instead of assuming it, and cleaning up only the process tree it started. It is MIT-licensed, has 140+ tests, and includes a recorded evaluation playback plus three evidence-linked case studies.

The skill runtime sends no telemetry and makes no network calls. Installation uses the third-party skills CLI, which records anonymous, opt-out install telemetry:

npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy

Project: https://github.com/pntech20/resource-safe-execution
```

## Reddit

Re-check every linked rule page immediately before posting. Reddit drafts require
manual account-holder posting; do not use bots or posting automation.

### r/ClaudeAI

Rules: https://www.reddit.com/r/ClaudeAI/about/rules.json

Flair: `Claude Code`

Status: **DO NOT POST**

The current showcase gate requires truthful evidence that a project was built
with Claude or Claude Code, or specifically for Claude, plus an explanation of
Claude's role. This multi-client project does not establish that provenance.
The account-holder karma gate would also need to be checked. Do not invent
Claude involvement; reconsider only if independently verifiable provenance
satisfies the live rules.

### r/ClaudeCode

Rules: https://www.reddit.com/r/ClaudeCode/about/rules.json

Flair: `Resource`

Disclosure: function is resource-safe heavy local agent work; beneficiaries are
developers running such work; cost is free; relationship is project maker and
maintainer.

```text
I built Resource Safe Execution after my own workstation became unusable while agents, emulators, and browser workers competed for resources.

Function: it helps Claude Code and other coding agents derive concurrency from current headroom, verify real GPU use, and clean up only owned process trees. Beneficiaries: developers running resource-intensive local agent work. Cost: free and MIT-licensed. Relationship: I built and maintain it.

The project has 140+ tests and a 38-second recorded evaluation. The skill runtime sends no telemetry and makes no network calls. The third-party skills CLI records anonymous, opt-out install telemetry.

Project, demo, evidence, and install command: https://github.com/pntech20/resource-safe-execution
```

### r/codex

Rules: https://www.reddit.com/r/codex/about/rules.json

Flair: `Showcase`

Requirement: manual account-holder posting only; no bots or automated
submissions.

```text
I built Resource Safe Execution after my own workstation became unusable while agents, emulators, and browser workers competed for resources.

It gives Codex and other coding agents a repeatable workflow for heavy local tasks: inspect current headroom, choose a conservative concurrency bound, verify actual GPU use, and clean up only the process tree they own. It is MIT-licensed, has 140+ tests, and includes a 38-second recorded evaluation.

The skill runtime sends no telemetry and makes no network calls. The third-party skills CLI records anonymous, opt-out install telemetry.

Project, demo, evidence, and install command: https://github.com/pntech20/resource-safe-execution
```

### r/opensource

Rules: https://www.reddit.com/r/opensource/about/rules.json

Flair: `Promotional`

Status: **DO NOT POST**

The current rules classify AI-generated content as ban-worthy. This section
intentionally provides no ready-to-paste body. Reconsider only if the community
rules change and a human account holder writes an original post.

## Publish-day checklist

1. Re-read the live rules and verify account eligibility and flair.
2. Keep the maker relationship, cost, and telemetry boundary explicit.
3. Re-test the pinned command and open every evidence link.
4. Post manually with native media, no tracking parameters, bots, or automation.
5. Stay available for replies and correct any material error promptly.
