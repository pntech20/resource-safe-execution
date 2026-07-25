# Resource Safe Execution

## Let your AI agent run heavy jobs—without freezing your workstation.

Resource Safe Execution is a cross-platform Agent Skill that inspects CPU,
memory, disk, GPU visibility, and running processes; chooses bounded
concurrency; verifies acceleration instead of assuming it; and cleans up only
processes the agent started.

[![38-second recorded evaluation playback showing bounded execution and
ownership-safe cleanup](assets/launch/resource-safe-execution-demo.gif)](assets/launch/resource-safe-execution-demo.gif)

[**Watch the 38-second proof**](assets/launch/resource-safe-execution-demo.gif)
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

## Why

Resource-heavy coding tasks can make a workstation unresponsive, exhaust disk
space, or leave child processes behind. Resource Safe Execution gives an agent
a conservative workflow for inspecting the host, choosing bounded concurrency,
monitoring work, and cleaning up only processes it started.

## What it does

The canonical [Agent Skill](skills/resource-safe-execution) combines portable
policy with a Python 3.10+ probe for read-only host inspection of CPU, memory,
disk, GPU visibility, and privacy-preserving process summaries. On POSIX, its
only optional write is an explicitly requested output file. Windows v0.1
requires stdout because the standard library cannot create a file relative to
a held directory handle without an ancestor path race. Platform-specific
guidance is loaded from direct local links in the skill folder.

## Safety guarantees

The bundled runtime uses only the Python standard library. It performs no
network access, telemetry, package installation, or privilege escalation. It
never terminates pre-existing or unrelated processes. Diagnostic calls have a
five-second execution deadline plus a fixed 0.25-second cleanup grace. The
parent drains stdout and stderr through operating-system pipes without reader
threads or backing files, then closes them when the owned child exits. This
keeps at most one MiB of retained captured bytes plus
operating-system-bounded pipe buffers, so descendant-held standard handles
cannot extend the call. It does not bound the total bytes a child may attempt
to write; the first observed byte above the retained limit is an output
overflow. A timeout or overflow is a breach. Windows then stops only the child
through its owned process handle, while POSIX stops the new owned process
group.

Diagnostic executables never come from the project directory or inherited
PATH. Native Windows APIs provide the Windows and Program Files anchors; the
probe rejects reparse or current-token-writable trusted components and passes
only validated SystemRoot, WINDIR, ProgramFiles, and system-only
`PSModulePath` values. That module path excludes current-user PowerShell module
roots so `Get-CimInstance` cannot auto-load a user shadow. A Windows access
probe treats only `ERROR_ACCESS_DENIED` and `ERROR_PRIVILEGE_NOT_HELD` as
definitive absence of a requested dangerous right; sharing and transient
errors fail closed. POSIX candidates must be root-owned, executable, and
beneath a root-owned ancestor chain that is not group/other-writable or
exposed through a detectable ACL. Privileged system-directory mutation is
outside this unprivileged-shadowing boundary.

Process summaries exclude command lines, environment variables, usernames,
file contents, tokens, and network destinations. Detection of GPU hardware is
not presented as proof that an application uses a particular acceleration
backend.

## Detailed manual installation

Review all executable skill contents, especially
`scripts/resource_probe.py`, before installation.

The safe default is a reviewed, checksum-verified copy:

1. Use the exact reviewed release checkout.
2. Verify the nine paths and SHA-256 hashes in the
   [installation manifest](skill-manifest.json) against
   [SHA256SUMS](SHA256SUMS).
3. Copy only those nine manifest-listed regular files, then verify the
   destination contains exactly the same paths and hashes.

Use the appropriate destination root:

| Client and scope | Destination |
| --- | --- |
| Codex project | `.agents/skills/resource-safe-execution` |
| Codex personal | `~/.agents/skills/resource-safe-execution` |
| Claude project | `.claude/skills/resource-safe-execution` |
| Claude personal | `~/.claude/skills/resource-safe-execution` |
| Antigravity workspace | `.agents/skills/resource-safe-execution` |
| Antigravity global | `~/.gemini/config/skills/resource-safe-execution` |

## Agent compatibility

The canonical folder follows the open
[Agent Skills specification](https://agentskills.io/specification). The
documented destinations come from the official
[Codex](https://developers.openai.com/codex/skills),
[Claude Code](https://code.claude.com/docs/en/skills), and
[Antigravity](https://antigravity.google/docs/skills) skill documentation.

Repository tests provide format and install validation for clean copies. They
are not actual client runtime validation. See the
[compatibility evidence and limits](docs/compatibility.md) before making a
client-specific claim.

### Release status

The release is `v0.1.0`. All 17 required skill-enabled behavior
signals are present in the [auditable evaluation](docs/evaluations/2026-07-24-skill-enabled.md),
and final-review provenance is hash-checked by the repository suite. The
local Codex installation contains the exact nine manifest-listed files.

Windows was physically exercised on this host with the live probe, both
validators, and the repository suite. The
[hosted CI run](https://github.com/pntech20/resource-safe-execution/actions/runs/30098155287)
passed all six Windows, macOS, and Ubuntu jobs on Python 3.10 and 3.13,
including a live JSON smoke probe. Physical macOS, physical Linux, Claude
Code, Antigravity, and other proprietary client runtime checks remain
unperformed; no physical-host or client-runtime claim is inferred from CI.

## Run the probe directly

```powershell
python skills/resource-safe-execution/scripts/resource_probe.py --format json
```

The probe prints one JSON document. On macOS and Linux,
`--output NEW_FILE` performs an optional output-file write using POSIX
directory-handle-relative, no-follow traversal and exclusive creation. It
refuses existing files, symlinks, and invalid parent paths even if an ancestor
is swapped concurrently. Windows v0.1 requires stdout and rejects `--output`
with exit code `1`. Missing host metrics degrade individually with a
machine-readable reason.

## Validate

```powershell
python -m compileall skills tests
python -m unittest discover -s tests -v
python tests/validate_skill.py skills/resource-safe-execution
```

Project releases use semantic versioning. The probe's JSON schema version
changes only for incompatible data-contract changes; it is independent of
documentation-only project releases.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change. Report
vulnerabilities privately according to [SECURITY.md](SECURITY.md).

## License

Resource Safe Execution is available under the [MIT License](LICENSE).
