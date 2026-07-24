# Resource Safe Execution

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

## Install

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

The open [`skills`](https://github.com/vercel-labs/skills) installer is a
convenience-only remote route. Copy-layout tests do not exercise it:

```powershell
npx --yes skills@1.5.20 add https://github.com/pntech20/resource-safe-execution/tree/v0.1.0/skills/resource-safe-execution --skill resource-safe-execution --copy
```

Review the installed files again before allowing an agent to execute them.

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

The release candidate remains `v0.1.0`. All 17 required skill-enabled behavior
signals are present in the [auditable evaluation](docs/evaluations/2026-07-24-skill-enabled.md),
and final-review provenance is hash-checked by the repository suite. The
existing local Codex installation was not overwritten during final review.

Windows was physically exercised on this host with the live probe, both
validators, and the repository suite. macOS and Linux have deterministic
fixture coverage and configured hosted CI, but those hosted jobs have not
completed. Claude Code, Antigravity, physical macOS, physical Linux, and
proprietary client runtime checks remain unperformed; no runtime compatibility
claim is made.

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
