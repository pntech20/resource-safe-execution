# Resource Safe Execution: 1,000-Install Growth Design

**Date:** 2026-07-25  
**Status:** Approved through the user's automatic-selection instruction  
**Campaign window:** 30 days  
**Primary goal:** 1,000 installs recorded for `pntech20/resource-safe-execution` by the `skills` CLI

## 1. Objective and audience

The campaign targets individual users of Codex, Claude Code, Antigravity, Cursor,
and other Agent Skills-compatible tools who run CPU-, memory-, disk-, GPU-,
browser-, emulator-, or process-intensive work on a personal workstation.

The campaign does not promise virality. It creates a measurable install funnel
and maximizes the probability of compounding discovery.

The primary metric is the deduplicated install count attributed to the repository
by skills.sh. This is aggregated telemetry from the third-party `skills` CLI,
not telemetry in Resource Safe Execution. The skill itself remains local,
network-free, and telemetry-free.

## 2. Positioning

### Primary message

**Let your AI agent run heavy jobs—without freezing your workstation.**

### Supporting message

Resource Safe Execution is a cross-platform Agent Skill that inspects CPU, RAM,
disk, GPU visibility, and running processes; chooses bounded concurrency;
requires acceleration to be verified; and cleans up only processes the agent
started.

### Ten-second pitch

Install one Agent Skill and your coding agent will check available resources,
cap parallel work, verify GPU use, and clean up only what it started—with no
dependencies, network calls, or telemetry.

### Proof strip

- No telemetry
- No network access
- Python standard library only
- SHA-256 release manifest
- Windows, macOS, and Linux CI

Physical-host and proprietary-client claims remain limited to the evidence
actually collected by the project.

## 3. Considered approaches

### A. Install-led launch — selected

Lead every asset with one canonical `npx skills add` command, make the repository
convert visitors into installs, seed genuine beta installs, and use the
skills.sh leaderboard as the compounding discovery surface.

**Strength:** Directly optimizes the selected metric.  
**Trade-off:** Requires excellent onboarding and a real visual demonstration.

### B. Credibility-first technical launch

Lead with evaluations, security properties, and a long technical article.

**Strength:** Strong trust and durable search value.  
**Trade-off:** The current repository already has substantial proof; more proof
without a shorter install funnel is unlikely to produce 1,000 installs quickly.

### C. Marketplace-first launch

Wait for OpenAI and Claude directory acceptance before broader promotion.

**Strength:** High-trust distribution if accepted.  
**Trade-off:** Review timelines are undocumented and outside the maintainer's
control, so this cannot be the critical path for a 30-day target.

The selected design uses A as the core, B as conversion proof, and C as a
parallel long-term distribution track.

## 4. Funnel design

```text
Qualified impression
  -> repository or skills.sh page
  -> 30-second proof
  -> canonical CLI install
  -> successful local preflight
  -> first real workload
  -> optional testimonial or setup report
```

Every campaign asset links to the same install section. The primary path is:

```powershell
npx --yes skills@1.5.20 add pntech20/resource-safe-execution `
  --skill resource-safe-execution --copy
```

The README also retains an adjacent audited path pinned to `v0.1.0`, with
manifest and checksum verification. The fast path must not obscure the security
trade-off of fetching and executing a third-party installer.

The activation prompt is:

> Before running this build and eight browser workers, inspect my machine,
> choose a safe profile, track every process you launch, and clean up only your
> owned tree.

## 5. Repository conversion surface

The first README screen contains, in this order:

1. Outcome-led headline and one-sentence explanation.
2. A real 30–45 second demo GIF or video.
3. The canonical install command and smoke test.
4. The five-item trust strip.
5. One activation prompt and links to audited installation and full evidence.

The detailed threat model, platform implementation, and evidence stay in the
repository but move below the initial conversion surface.

Required discovery metadata:

- Description: `Cross-platform Agent Skill for bounded concurrency, verified GPU use, and ownership-safe process cleanup.`
- Topics: `agent-skills`, `ai-agents`, `codex`, `claude-code`,
  `antigravity`, `resource-management`, `gpu`, `process-management`
- A 1280×640 solid-background social preview
- Discussions categories for install help, setups, and benchmarks
- Issue forms for bugs and compatibility reports
- A skills.sh badge after the first genuine CLI install creates the listing

## 6. Demonstration design

The demo uses real recorded evaluation behavior rather than a mock interface.
It shows:

1. A request for eight workers and broad cleanup.
2. The skill running a read-only host preflight.
3. The agent selecting a conservative worker count.
4. GPU hardware visibility being separated from backend-use verification.
5. Owned process IDs being recorded.
6. A refusal to terminate by broad process name.
7. Cleanup limited to the owned process tree.

The demo must not claim that the skill guarantees a fixed CPU percentage or
automatically accelerates an unsupported workload.

## 7. Distribution architecture

### Immediate: skills.sh and GitHub

- Create the listing through genuine `skills` CLI installs.
- Add the skills.sh badge and link directly to the skill page.
- Use exact GitHub topics, a social card, Discussions, and healthy-community
  files.
- Recruit 20–30 genuine beta users across at least four agent clients.

Installs must never be looped, automated, purchased, or otherwise manufactured.

### Parallel: Claude Code

- Add `.claude-plugin/plugin.json`.
- Add `.claude-plugin/marketplace.json` so users can install from the GitHub
  repository as a self-hosted marketplace.
- Validate with Claude's plugin validator and test the copied plugin in a real
  Claude Code runtime.
- Submit to the public Claude community directory. Do not claim inclusion until
  acceptance is visible.

### Parallel: OpenAI/ChatGPT/Codex

- Add `.codex-plugin/plugin.json` and package the skill as an OpenAI plugin.
- Prepare publisher identity, logo, category, starter prompts, positive and
  negative tests, support URL, privacy URL, terms URL, availability, and release
  notes.
- Run the official local/plugin validation flow and submit for review.
- Treat acceptance as upside, not a dependency of the 30-day campaign.

### Antigravity

- Keep the documented direct install into `.agents/skills` and the global
  Antigravity skill directory.
- Add a verified client-specific walkthrough after a real runtime test.
- Do not imply a public Antigravity marketplace exists without official
  documentation.

## 8. Thirty-day launch sequence

### Days 1–3: conversion foundation

- Rewrite the README's first screen.
- Create the demo and social preview.
- Verify the canonical install and uninstall paths in clean environments.
- Create the skills.sh listing, badge, metadata, Discussions, and issue forms.
- Add OpenAI and Claude plugin packaging.

### Days 4–7: genuine beta installs

- Recruit 20–30 users across Codex, Claude Code, Antigravity, and at least one
  additional compatible agent.
- Ask each tester to install with the canonical command and run one real task.
- Fix onboarding failures before public promotion.
- Collect permissioned, machine-redacted outcomes using a consistent template.

### Days 8–14: proof wave

- Publish one canonical technical case study covering the problem, baseline,
  skill behavior, failure cases, safety boundaries, and install command.
- Publish distinct native screen-demo posts on X and LinkedIn at least 24 hours
  apart.
- Cross-post the article only where canonical-link support is available.

### Days 15–21: community launch

- Publish tailored, authorship-disclosed case studies to relevant Reddit
  communities only when their rules and moderator guidance permit it.
- Submit a Show HN only when the repository is immediately runnable and the
  maker can answer questions for four to six hours.
- Share in designated showcase channels after participating genuinely in those
  communities.

### Days 22–30: long tail

- Publish what early users changed and what failed.
- Submit to relevant awesome lists only after meeting their contribution and
  social-proof requirements.
- Use Product Hunt only if the project has become a polished, immediately usable
  product experience; a plain documentation listing is insufficient.
- Refresh the demo and headline using actual conversion feedback.

## 9. Measurement

### Primary

- skills.sh install count for `pntech20/resource-safe-execution`
- Target: 1,000 by campaign day 30

### Leading indicators

- 40,000 qualified impressions
- 3,200 repository or skills.sh visits
- 1,400 installer starts
- 1,000 recorded CLI installs

### Quality indicators

- At least 20 beta users complete one real workload.
- At least four agent clients receive genuine runtime evidence.
- Install-related issues are acknowledged within 24 hours during launch week.
- Opt-in testimonials include client, workload, selected profile, and outcome.

GitHub traffic, release downloads, stars, forks, and marketplace acceptance are
secondary indicators. They must not be represented as verified installs.

## 10. Safety and community constraints

- No silent telemetry is added to the skill.
- The skills.sh/CLI telemetry distinction is stated clearly.
- No coordinated voting, engagement pods, purchased traffic, automated
  self-promotion, duplicate posts, or unsolicited mass messages.
- Every community post is written for that community, discloses authorship, and
  follows local rules.
- No compatibility, performance, or physical-host claim exceeds collected
  evidence.
- Vulnerabilities continue to use the private route in `SECURITY.md`.

## 11. Verification and failure handling

Before promotion:

- Run the repository's full test and validation suite.
- Test fast and audited installs from clean temporary directories.
- Verify every README command and outbound link.
- Validate OpenAI and Claude plugin manifests with their official tooling.
- Check the social card and demo at desktop and mobile widths.
- Confirm that the skills.sh source, slug, badge, and count refer to this
  repository rather than a fork or duplicate.

If install conversion is below 30% after 500 qualified repository visits, stop
expanding distribution and fix the README/demo/install path. If activation
feedback identifies a safety or compatibility defect, pause promotion, publish
the limit, fix it, and re-verify before resuming.

## 12. Authority boundary

Repository changes, release assets, marketplace packages, draft submissions,
and draft campaign copy can be prepared automatically. Publishing from personal
social accounts, representing the maintainer in community discussions, and
accepting marketplace legal terms require the account holder or explicit
delegated authority at the time of the action.

## 13. Primary reference anchors

- [skills.sh ranking and badge](https://www.skills.sh/docs)
- [skills.sh CLI](https://www.skills.sh/docs/cli)
- [OpenAI skill authoring and plugin distribution](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [OpenAI plugin submission](https://developers.openai.com/plugins/deploy/submission)
- [Claude Code plugin creation](https://code.claude.com/docs/en/plugins)
- [Claude Code marketplace distribution](https://code.claude.com/docs/en/plugin-marketplaces)
- [Antigravity Agent Skills](https://antigravity.google/docs/skills)
- [GitHub topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)
- [GitHub social previews](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
- [Show HN guidelines](https://news.ycombinator.com/showhn.html)
