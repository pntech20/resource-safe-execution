# Marketplace submission readiness

This document prepares evidence for OpenAI and Claude marketplace review. It is
not proof of client runtime behavior, directory acceptance, or a promised review
timeline. No external submission was performed.

Status meanings:

- **Ready**: the repository contains the named input; re-check it before upload.
- **Target URL**: the stable public URL is selected, but publication must still
  be verified.
- **Unavailable / not run**: the required client, portal, or authenticated
  operation was unavailable in this work session.
- **Account-holder gate**: only the account holder may verify identity,
  permissions, legal terms, availability, or submit.
- **Not submitted / Not accepted**: no directory-review outcome exists.

## OpenAI readiness checklist

| Done | Submission input | Current status | Evidence or required action |
| --- | --- | --- | --- |
| [ ] | Verified publisher identity | Account-holder gate | Not verified in this work session. The account holder must verify the publisher identity shown in the portal. |
| [ ] | Apps Management: Write permission | Account-holder gate | Not verified. The account holder must confirm the submitting account has this permission. |
| [x] | Plugin name | Ready | `resource-safe-execution` from `.codex-plugin/plugin.json`. |
| [x] | Short description | Ready | `Run heavy agent work without freezing your machine.` |
| [x] | Long description | Ready | `Plan and run CPU-, memory-, disk-, GPU-, browser-, emulator-, and process-intensive work with bounded concurrency and ownership-safe cleanup.` |
| [ ] | Logo | Unavailable / not run | No dedicated marketplace logo is present. Do not substitute the social preview unless the portal explicitly permits it. |
| [x] | Category | Ready | `Developer Tools`; re-check the portal's current allowed categories. |
| [x] | Website URL | Ready | <https://github.com/pntech20/resource-safe-execution> |
| [ ] | Support URL | Target URL | <https://github.com/pntech20/resource-safe-execution/blob/main/SUPPORT.md>; verify the public page before submission. |
| [ ] | Privacy URL | Target URL | <https://github.com/pntech20/resource-safe-execution/blob/main/PRIVACY.md>; verify the public page before submission. |
| [ ] | Terms URL | Target URL | <https://github.com/pntech20/resource-safe-execution/blob/main/TERMS.md>; verify the public page before submission. |
| [ ] | Skill bundle/ZIP | Not built | Build the upload from the reviewed repository state, retain the canonical `skills/resource-safe-execution/` payload, and record its checksum. |
| [x] | Starter prompts | Ready | The manifest contains three starter prompts; re-read them against the activation cases below. |
| [ ] | Five positive activation tests | Defined / not run | Execute P1–P5 in the submitted client version and record the observed result. |
| [ ] | Three negative/non-activation tests | Defined / not run | Execute N1–N3 and verify ordinary edits do not activate the skill solely because they are code tasks. |
| [ ] | Availability and release notes | Account-holder gate | Proposed version is `0.2.0`; the account holder must choose availability and approve final release notes. |
| [ ] | Automated policy/security scan | Unavailable / not run | The authenticated submission scan was not run. Record its exact result before submission. |

Current OpenAI directory status: **Not submitted** and **Not accepted**.

## Claude readiness checklist

| Done | Submission input | Current status | Evidence or required action |
| --- | --- | --- | --- |
| [ ] | `claude plugin validate .` | Unavailable / not run | No official validator output was collected in this work session. Do not call repository JSON tests official Claude validation. |
| [ ] | Clean `claude --plugin-dir .` runtime test | Unavailable / not run | No Claude client loaded and used this plugin in this work session. |
| [ ] | Self-hosted marketplace install | Unavailable / not run | No clean marketplace add/install test was performed in this work session. |
| [x] | Repository | Ready | <https://github.com/pntech20/resource-safe-execution> |
| [x] | Homepage | Ready | <https://github.com/pntech20/resource-safe-execution> |
| [x] | License | Ready | `MIT` |
| [x] | Author | Ready | `pntech20` |
| [x] | Version | Ready | `0.2.0` in both Claude metadata files. |
| [ ] | Public community-directory submission form | Account-holder gate | Re-check the current form, identity requirements, and terms; the account holder submits. |

The self-hosted marketplace is described by
`.claude-plugin/marketplace.json`. The `claude-plugins-official` repository is
not an intake route: **`claude-plugins-official` has no application process**.
Use the public community plugin form only after the account-holder gate.

Current Claude directory status: **Not submitted** and **Not accepted**.

## Activation test matrix

Run these cases in a clean session on the exact candidate version. Record
whether the skill loaded, the visible reason, and the resulting plan. Do not
infer activation from manifest validity.

| ID | Prompt | Expected behavior | Required evidence |
| --- | --- | --- | --- |
| P1 | Run eight browser workers on this laptop. | Activate resource-safe planning; inspect the host and derive a bounded worker cap instead of assuming eight is safe. | Client/version, activation observation, selected gates/profile, redacted output. |
| P2 | Choose safe parallelism for this build. | Activate resource-safe planning; inspect current headroom and choose bounded concurrency. | Client/version, activation observation, input gates, redacted output. |
| P3 | Check whether my ML workload really uses the GPU. | Activate resource-safe planning; distinguish device visibility from verified application-backend use. | Client/version, activation observation, verification ladder/result, redacted output. |
| P4 | Stop the emulator and only processes you started. | Activate resource-safe planning; require an ownership record and refuse broad name-based cleanup. | Client/version, activation observation, ownership decision, redacted output. |
| P5 | Inspect disk pressure before generating large artifacts. | Activate resource-safe planning; perform read-only preflight before the workload. | Client/version, activation observation, disk gate/result, redacted output. |
| N1 | Rewrite this function for readability. | Do not load the skill solely for this ordinary code edit. | Client/version and observed non-activation. |
| N2 | Summarize this Markdown file. | Do not load the skill solely for this ordinary document task. | Client/version and observed non-activation. |
| N3 | Rename this CSS class. | Do not load the skill solely for this ordinary code edit. | Client/version and observed non-activation. |

Positive cases must activate resource-safe planning.
Negative cases must not load the skill solely because they are ordinary code edits.

## Validation evidence record

Preserve exact output rather than a paraphrase. A format-only check must be
labelled format-only and must never be reported as client runtime validation.

| Track | Status | Client/tool version | Command or action | Exit code | Exact output | Date |
| --- | --- | --- | --- | --- | --- | --- |
| GitHub skill publisher dry-run | Passed with warnings—format/package only | `gh skill publish` preview; version not captured | `gh skill publish --dry-run` from repository root | `0` | `warning resource-safe-execution recommended field missing: license`; `warning no active tag protection rulesets found`; `Dry run complete. Use without --dry-run to publish.` | 2026-07-25 |
| OpenAI local plugin package validator | Passed—format/package only | Bundled Codex `plugin-creator` validator; version not exposed | `python .../plugin-creator/scripts/validate_plugin.py .` | `0` | `Plugin validation passed: <REPOSITORY_ROOT>`; local path redacted | 2026-07-25 |
| Canonical repository skill validator | Passed—format/package only | Repository validator at current commit | `python tests/validate_skill.py skills/resource-safe-execution` | `0` | `Valid skill: skills\resource-safe-execution` | 2026-07-25 |
| Agent Skills quick validator | Passed—format/package only | Bundled `skill-creator` validator; version not exposed | `python .../skill-creator/scripts/quick_validate.py skills/resource-safe-execution` | `0` | `Skill is valid!` | 2026-07-25 |
| OpenAI automated policy/security scan | Unavailable / not run | Unavailable | Authenticated portal scan | Not run | Not available; portal action was not performed. | Not run |
| Claude plugin validator | Unavailable / not run | Unavailable | `claude plugin validate .` | Not run | Not available; official validator was not run. | Not run |
| Claude direct plugin runtime | Unavailable / not run | Unavailable | `claude --plugin-dir .` in a clean session | Not run | Not available; client runtime test was not run. | Not run |
| Claude self-hosted marketplace install | Unavailable / not run | Unavailable | Clean marketplace add and plugin install | Not run | Not available; install test was not run. | Not run |

For each future run, replace one row's unavailable values only with the exact
client/tool version, command or portal action, exit code where applicable,
verbatim bounded output, date, and redacted artifact location. Add activation
case IDs and observed results to the same evidence record.

These three passing local validators establish repository format and package
integrity only. They do not establish OpenAI portal policy-scan success, Claude
validator success, client activation, client runtime behavior, directory
submission, or acceptance.

The GitHub dry-run also passed. Its optional `license` warning is intentionally
deferred because adding frontmatter would change the checksum-audited v0.1.0
canonical payload during a distribution-only change. The tag-protection warning
requires repository-owner governance review; it is not a skill validation
failure.

## Account-holder submission gate

Before any upload, the account holder must:

1. Verify publisher identity and Apps Management: Write permission.
2. Open the website, support, privacy, and legal links from a public session.
3. Review availability, release notes, directory presentation, and all terms.
4. Confirm the skill bundle checksum and the exact version being submitted.
5. Review validator, runtime, activation, and automated scan evidence without
   upgrading format-only checks into runtime claims.

Only after that explicit review may the account holder upload OpenAI through
the Platform submission portal or submit Claude through the public community plugin form.
No worker in this repository may accept terms or publish through a personal
account by implication.

No external submission was performed. Both tracks remain **Not submitted** and
**Not accepted**. Do not claim acceptance until the public listing is visible.
No approval SLA is promised.
