# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use the repository's
GitHub **Security** tab to submit a private vulnerability report through GitHub
Security Advisories. Include affected versions, impact, reproduction steps,
and any suggested mitigation. Avoid including real secrets or unrelated
personal data.

## Runtime boundary

The probe performs read-only host inspection. On POSIX, one explicit optional
output-file write uses POSIX directory-handle-relative no-follow traversal and
creates a new regular file exclusively. Windows v0.1 requires stdout and
rejects `--output`; this fail-closed boundary avoids claiming race-safe
arbitrary-parent creation through path-based Win32 APIs.

The runtime performs no network access, telemetry, package installation, or
privilege escalation. It never terminates pre-existing or unrelated processes.
Each diagnostic call has at most a five-second execution deadline and a fixed
0.25-second cleanup grace. Anonymous temporary capture files mean
descendant-held standard handles cannot block cleanup. The probe retains no
more than one MiB of combined output. A timeout or output overflow is a breach;
the probe then stops only the Windows child represented by its owned process
handle or the POSIX process group that it created for that child.

Native Windows APIs supply trusted directory anchors; inherited PATH and
mutable SystemRoot, WINDIR, and ProgramFiles inputs are ignored. Reparse points
and current-token-writable trusted components are rejected. POSIX executable
and ancestor metadata must show root ownership, no group/other write access,
and no detectable ACL/current-user write grant. This protects against
unprivileged project, PATH, and environment shadowing. Privileged
system-directory mutation, kernel compromise, and replacement by an actor who
can already modify validated system directories remain outside the boundary.

The probe does not expose command lines, environment variables, usernames,
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
