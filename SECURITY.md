# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use the repository's
GitHub **Security** tab to submit a private vulnerability report through GitHub
Security Advisories. Include affected versions, impact, reproduction steps,
and any suggested mitigation. Avoid including real secrets or unrelated
personal data.

## Runtime boundary

The probe performs read-only host inspection, with one explicit optional
output-file write that creates a new regular file exclusively. It performs no
network access, telemetry, package installation, or privilege escalation. It
never terminates pre-existing or unrelated processes; it may stop only its own
diagnostic child after the five-second timeout or one-MiB combined-output bound
overflows. It does not expose command lines, environment variables, usernames,
file contents, tokens, or network destinations in process summaries. Reports
that cross this boundary are security-sensitive.

## Supported releases

Security support covers the latest released minor version of the current major
release. Maintainers may provide a patch for an older release when the risk and
backport complexity justify it, but older releases are not guaranteed support.
Unreleased development snapshots receive fixes on the default branch.

## Response targets

Maintainers target acknowledgment within 3 business days, initial triage within
7 business days, and a status update at least every 14 days while an accepted
report remains open. These are response targets, not guarantees of resolution.
Resolution timing depends on severity, reproducibility, and release risk.
