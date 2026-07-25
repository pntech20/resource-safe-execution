# Growth Distribution Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the skills.sh discovery surface, complete GitHub metadata, prepare marketplace submissions, recruit genuine beta installs, and operate an ethical 30-day campaign toward 1,000 recorded installs.

**Architecture:** Treat skills.sh's deduplicated repository install count as the primary KPI, use GitHub as the canonical trust and support surface, run marketplace review tracks in parallel, and keep all personal-account publishing behind an explicit account-holder boundary.

**Tech Stack:** `skills` CLI 1.5.20, skills.sh, GitHub CLI/API/UI, Claude Code marketplace, OpenAI plugin portal, Markdown/CSV operating documents.

## Global Constraints

- Never automate, purchase, loop, or incentivize installs, votes, stars, or comments.
- Resource Safe Execution remains telemetry-free; disclose that skills.sh counts anonymous `skills` CLI install events.
- Do not publish from a personal account or accept marketplace legal terms without the account holder.
- Use only community-specific posts allowed by current rules.
- Do not claim directory acceptance before the public listing is visible.
- Do not claim a client runtime test unless that client actually loaded and used the skill.
- Pause promotion for a safety or compatibility defect until it is fixed and re-verified.

---

## File structure

- Modify `README.md`: add the live skills.sh badge and page after indexing.
- Create `docs/launch/beta-test.md`: tester procedure and redacted outcome template.
- Create `docs/launch/metrics.csv`: daily campaign ledger with no personal data.
- Create `docs/launch/marketplace-submission.md`: readiness checklist and submission evidence.
- Create `docs/launch/community-matrix.md`: current rules, status, owner, and post date.
- Create `SUPPORT.md`: public support scope and routes.
- Create `PRIVACY.md`: skill and installer telemetry boundary.
- Create `TERMS.md`: open-source use and warranty boundary without replacing the MIT license.

### Task 1: Create the skills.sh listing and metric baseline

**Files:**
- Modify: `README.md`
- Create: `docs/launch/metrics.csv`

**Interfaces:**
- Consumes: the conversion-foundation install command.
- Produces: the primary discovery page, badge, and day-zero count.

- [ ] **Step 1: Perform one genuine clean CLI install**

From a temporary project that does not already contain this skill:

```powershell
npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy
```

Select only an agent actually installed on the machine. Inspect the copied files
and remove the temporary project after verification. Do not repeat the install
to inflate the count.

- [ ] **Step 2: Verify the listing**

Open:

```text
https://skills.sh/pntech20/resource-safe-execution/resource-safe-execution
```

If the page is not visible immediately, wait for the documented indexing delay
and check once per hour; do not create duplicate installs.

- [ ] **Step 3: Add the badge**

Add beneath the README title:

```markdown
[![skills.sh installs](https://skills.sh/b/pntech20/resource-safe-execution)](https://skills.sh/pntech20/resource-safe-execution/resource-safe-execution)
```

- [ ] **Step 4: Create the metric ledger**

```csv
date,skills_sh_installs,github_stars,github_forks,release_downloads,qualified_impressions,repository_visits,beta_workloads,notes
2026-07-25,0,1,0,0,0,0,0,"Pre-listing campaign baseline; refresh public counters immediately before launch"
```

Refresh the public counters once immediately before launch. Store no usernames,
IP addresses, emails, or client identifiers.

- [ ] **Step 5: Commit**

```powershell
git add README.md docs/launch/metrics.csv
git commit -m "docs: add skills.sh install surface"
```

### Task 2: Complete GitHub discovery and support metadata

**Files:**
- Create: `SUPPORT.md`
- Create: `PRIVACY.md`
- Create: `TERMS.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: social preview from the launch-assets plan and existing
  `SECURITY.md`/`LICENSE`.
- Produces: complete public repository metadata and stable submission URLs.

- [ ] **Step 1: Create support, privacy, and terms pages**

`SUPPORT.md` must route:

- reproducible bugs to the bug form;
- compatibility evidence to the compatibility form;
- usage questions to Discussions;
- vulnerabilities to private security advisories.

`PRIVACY.md` must state:

- the skill performs no network access or telemetry;
- the optional third-party `skills` CLI records anonymous, opt-out install
  telemetry for skills.sh;
- GitHub, OpenAI, Anthropic, Google, and social platforms apply their own
  privacy policies when users access those services.

`TERMS.md` must state that the software is provided under MIT, that the MIT
license controls the code, that the project provides guidance rather than an
availability/performance guarantee, and that third-party services have separate
terms. Do not invent a company identity or collect acceptance.

- [ ] **Step 2: Update GitHub description, topics, and Discussions**

```powershell
gh repo edit pntech20/resource-safe-execution `
  --description "Cross-platform Agent Skill for bounded concurrency, verified GPU use, and ownership-safe process cleanup." `
  --enable-discussions `
  --add-topic agent-skills `
  --add-topic ai-agents `
  --add-topic codex `
  --add-topic claude-code `
  --add-topic antigravity `
  --add-topic resource-management `
  --add-topic gpu `
  --add-topic process-management
```

Read the result back with `gh repo view --json
description,repositoryTopics,hasDiscussionsEnabled`.

- [ ] **Step 3: Upload the social preview**

In repository Settings → General → Social preview, upload:

```text
assets/launch/resource-safe-execution-social-preview.png
```

GitHub has no stable documented `gh repo edit` flag for this upload. Use the
authenticated UI and verify the public Open Graph image changed.

- [ ] **Step 4: Add stable support/legal links to README**

Add compact links near Contributing and Security:

```markdown
[Support](SUPPORT.md) · [Privacy](PRIVACY.md) · [Terms](TERMS.md)
```

- [ ] **Step 5: Commit and verify**

```powershell
git add README.md SUPPORT.md PRIVACY.md TERMS.md
git commit -m "docs: complete public support and policy surface"
git status --short
```

Expected: clean.

### Task 3: Recruit and verify 20–30 beta installs

**Files:**
- Create: `docs/launch/beta-test.md`
- Modify: `docs/launch/metrics.csv`
- Modify: `docs/compatibility.md` only for verified evidence.

**Interfaces:**
- Consumes: canonical install, activation prompt, issue forms.
- Produces: onboarding defects, real workloads, and permissioned evidence.

- [ ] **Step 1: Write the beta procedure**

```markdown
# 15-minute beta test

1. Record OS and agent client/version without a username or machine name.
2. Install with the canonical `npx skills` command.
3. Confirm the installed folder and inspect `SKILL.md` and the probe.
4. Start a fresh agent session and use the activation prompt.
5. Run one real resource-intensive task you already intended to perform.
6. Record whether the skill activated, which profile it chose, whether GPU use
   was verified or left unproven, and whether cleanup was limited to owned work.
7. Remove command lines, paths, tokens, usernames, and unrelated processes.
8. Submit the compatibility form or report "no issue."
```

Add an explicit opt-in checkbox for quoting anonymized outcomes.

- [ ] **Step 2: Recruit across clients**

Target:

- 5–8 Codex users;
- 5–8 Claude Code users;
- 4–6 Antigravity users;
- 4–8 users across Cursor, Gemini CLI, OpenCode, or another compatible client.

Use existing professional/community relationships only. Do not mass-message
strangers.

- [ ] **Step 3: Triage onboarding defects**

For each defect, create one reproducible issue, fix and verify it before inviting
the next batch. Security defects pause all recruiting.

- [ ] **Step 4: Update evidence honestly**

Add a client/runtime row to `docs/compatibility.md` only when the report includes
client version, OS, install method, activation evidence, and observed outcome.
Label community-reported versus maintainer-reproduced evidence.

- [ ] **Step 5: Update aggregate metrics**

Increment only `beta_workloads` and public counters. Do not add tester identities
to `metrics.csv`.

- [ ] **Step 6: Commit documentation changes**

```powershell
git add docs/launch/beta-test.md docs/launch/metrics.csv docs/compatibility.md
git commit -m "docs: record beta installation evidence"
```

### Task 4: Prepare and validate marketplace submissions

**Files:**
- Create: `docs/launch/marketplace-submission.md`
- Modify: `docs/compatibility.md` only with actual validator/runtime evidence.

**Interfaces:**
- Consumes: plugin manifests, support/privacy/terms URLs, demo, social preview,
  test suite, and canonical skill payload.
- Produces: submission-ready OpenAI and Claude evidence; it does not accept
  legal terms automatically.

- [ ] **Step 1: Create one readiness checklist**

For OpenAI, include:

- verified publisher identity;
- Apps Management: Write permission;
- plugin name, short/long descriptions, logo, category;
- website, support, privacy, and terms URLs;
- skill bundle/ZIP;
- starter prompts;
- five positive activation tests;
- three negative/non-activation tests;
- availability and release notes;
- automated policy/security scan result.

For Claude, include:

- `claude plugin validate .` output;
- clean `claude --plugin-dir .` runtime test;
- self-hosted marketplace install test;
- repository, homepage, license, author, version;
- public community-directory submission form;
- explicit note that `claude-plugins-official` has no application process.

- [ ] **Step 2: Use these activation test cases**

Positive:

1. Run eight browser workers on this laptop.
2. Choose safe parallelism for this build.
3. Check whether my ML workload really uses the GPU.
4. Stop the emulator and only processes you started.
5. Inspect disk pressure before generating large artifacts.

Negative:

1. Rewrite this function for readability.
2. Summarize this Markdown file.
3. Rename this CSS class.

Expected: positive tasks activate resource-safe planning; negative tasks do not
load the skill solely because they are ordinary code edits.

- [ ] **Step 3: Validate in each available client**

Run official validators and record exact versions/output. Never replace an
unavailable client run with a format-only test while calling it runtime
validation.

- [ ] **Step 4: Submit only at the authority boundary**

The account holder reviews publisher identity, legal links, availability, and
terms. After that review:

- upload OpenAI through the Platform submission portal;
- submit Claude through the public community plugin form.

Record submission date and status. Do not promise an approval SLA.

- [ ] **Step 5: Commit readiness and evidence**

```powershell
git add docs/launch/marketplace-submission.md docs/compatibility.md
git commit -m "docs: prepare marketplace submissions"
```

### Task 5: Build the community operating matrix

**Files:**
- Create: `docs/launch/community-matrix.md`
- Modify: `docs/launch/metrics.csv`

**Interfaces:**
- Consumes: `docs/launch/campaign-copy.md` and current channel rules.
- Produces: a rule-checked publishing schedule; it does not post.

- [ ] **Step 1: Create the matrix**

Use columns:

```markdown
| Channel | Current rule URL | Eligible now? | Required disclosure/flair | Asset | Planned date | Published URL | Outcome |
```

Seed rows for skills.sh, GitHub, X, LinkedIn, DEV, Hashnode, Show HN, Product
Hunt, relevant Reddit communities, Cursor forum, and two awesome lists.

- [ ] **Step 2: Apply launch gates**

- Reddit: moderator/rule eligibility, authorship disclosure, community-specific
  content, no duplicate posts.
- Show HN: runnable product, maker presence for 4–6 hours, no vote solicitation.
- Product Hunt: usable product experience, genuine maker comment, no coordinated
  voting.
- Awesome lists: contribution thresholds and social proof met before PR.

- [ ] **Step 3: Lock the 30-day sequence**

- Days 1–3: repository, listing, metadata, assets.
- Days 4–7: beta installs and onboarding fixes.
- Days 8–14: article plus native X/LinkedIn demos.
- Days 15–21: tailored community posts and Show HN.
- Days 22–30: follow-up evidence and qualified directories/lists.

- [ ] **Step 4: Commit**

```powershell
git add docs/launch/community-matrix.md
git commit -m "docs: define rule-checked launch calendar"
```

### Task 6: Operate and evaluate the 30-day campaign

**Files:**
- Modify: `docs/launch/metrics.csv`
- Modify: `docs/launch/community-matrix.md`
- Modify: public docs only when new verified evidence changes them.

**Interfaces:**
- Consumes: all three growth plans.
- Produces: daily public metrics and evidence-driven funnel changes.

- [ ] **Step 1: Record the public baseline**

On day 0, record skills.sh installs, GitHub stars/forks, release downloads,
GitHub unique visitors where available, and beta workloads.

- [ ] **Step 2: Publish only through the account-holder boundary**

The account holder posts or explicitly delegates each personal-account action.
Use the prepared native asset and channel-specific copy. Remove tracking
parameters and remain available for responses.

- [ ] **Step 3: Update the ledger daily**

One row per calendar day. Use public aggregate counts only. Add a short note for
the day's distribution event or onboarding change.

- [ ] **Step 4: Apply the conversion stop rule**

After 500 qualified repository visits, if fewer than 150 result in recorded
installs, pause new-channel promotion. Fix the headline, demo, or install path,
run a small beta retest, then resume.

- [ ] **Step 5: Apply the safety stop rule**

For a safety or compatibility defect:

1. pause promotion;
2. publish the affected scope;
3. create a reproducible test;
4. fix and run the full suite;
5. update evidence and resume only after verification.

- [ ] **Step 6: Publish the day-30 report**

Report:

- final skills.sh install count;
- stars/forks/downloads separately;
- beta workload/client coverage;
- marketplace statuses;
- onboarding defects fixed;
- claims or compatibility limits learned;
- next 30-day decision.

Do not merge distinct counters into a single "users" number.

- [ ] **Step 7: Commit the final aggregate report**

```powershell
git add docs/launch/metrics.csv docs/launch/community-matrix.md docs/launch/day-30-report.md
git commit -m "docs: report 30-day growth campaign"
```
