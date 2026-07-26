# 15-minute beta test

This guide defines a prospective test procedure. No beta outcomes or compatibility results have been collected by this guide, and the recruitment targets below are goals—not completed installs or results.

Use one real resource-intensive task you already intended to perform. Do not create repeated installs or artificial workloads to increase a counter. The Resource Safe Execution skill performs no network access or telemetry; the optional third-party `skills` CLI records anonymous, opt-out install telemetry for skills.sh.

## Procedure

1. **Minute 0–1 — Record the environment.** Record the operating system and agent client version without a username or machine name.
2. **Minute 1–3 — Install.** Run `npx --yes skills@1.5.20 add pntech20/resource-safe-execution --skill resource-safe-execution --copy`.
3. **Minute 3–4 — Inspect the copy.** Confirm the installed folder, then inspect `SKILL.md` and `scripts/resource_probe.py` before use.
4. **Minute 4–5 — Start fresh.** Open a fresh agent session and send: “Before running this build and eight browser workers, inspect my machine, choose a safe profile, track every process you launch, and clean up only your owned tree.”
5. **Minute 5–11 — Run intended work.** Run one resource-intensive task that was already planned; do not add work solely for this beta.
6. **Minute 11–13 — Record observations.** Record whether the skill activated, the selected profile, whether GPU use was verified or left unproven, and whether cleanup remained limited to owned work.
7. **Minute 13–14 — Redact.** Remove command lines, paths, tokens, usernames, machine names, IP addresses, client identifiers, and unrelated processes from every attachment and quotation.
8. **Minute 14–15 — Report.** Submit the [compatibility form](../../.github/ISSUE_TEMPLATE/compatibility_report.yml), file a reproducible [bug report](../../.github/ISSUE_TEMPLATE/bug_report.yml), or report “no issue.”

## Redacted outcome template

```text
Operating system:
Agent client version:
Install method:
Activation evidence:
Selected profile:
GPU use: verified / left unproven / not applicable
Owned-work cleanup evidence:
Observed outcome:
Issue URL or "no issue":
Evidence source: community-reported / maintainer-reproduced
```

Do not collect tester identities in this template or the campaign ledger. Do
not record names, handles, email addresses, usernames, machine names, IP
addresses, or client identifiers there. GitHub issues are public: GitHub
displays the reporter's account identity and processes service data under its
own privacy policy. Submit a public issue only if comfortable with that
visibility. Maintainers must not copy the reporter's handle into beta metrics
or compatibility aggregates.

Quote permission is optional and defaults to no:

- [ ] I opt in to an anonymized quote from the redacted outcome above. I understand that leaving this unchecked means the outcome will not be quoted.

## Evidence threshold

Add compatibility evidence only when a report includes all five required fields: client version, operating system, install method, activation evidence, and observed outcome. Label accepted evidence as `community-reported` or `maintainer-reproduced`; do not upgrade a community report to a maintainer result without reproduction.

Record aggregate counts only in campaign metrics. Do not add tester identities, attribute “no issue” reports to a person, or turn an install event into a client-runtime or compatibility claim.

## Recruitment targets and boundaries

These are recruitment targets, not a claim that anyone has been recruited, installed the skill, or completed a workload:

- 5–8 Codex users
- 5–8 Claude Code users
- 4–6 Antigravity users
- 4–8 users across Cursor, Gemini CLI, OpenCode, or another compatible client

Recruit through existing professional or community relationships only. Do not mass-message strangers, automate outreach, offer incentives, or request repeated installs.

## Defect and safety pause

For each onboarding defect, create one reproducible issue. Fix and verify it before inviting the next batch.

Security defects pause all recruiting. A safety or compatibility defect pauses promotion until the affected scope is published, a regression test reproduces the defect, the fix passes the full suite, and the evidence is updated.
