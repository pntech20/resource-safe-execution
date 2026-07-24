# Resource Safe Execution

## Why

Resource-heavy coding tasks can make a workstation unresponsive, exhaust disk
space, or leave child processes behind. Resource Safe Execution gives an agent
a conservative workflow for inspecting the host, choosing bounded concurrency,
monitoring work, and cleaning up only processes it started.

## What it does

The canonical [Agent Skill](skills/resource-safe-execution) combines portable
policy with a Python 3.10+ read-only probe for CPU, memory, disk, GPU visibility,
and process summaries. Platform-specific guidance is loaded from direct local
links in the skill folder.

## Safety guarantees

The bundled runtime uses only the Python standard library. It performs no
network access, telemetry, package installation, privilege escalation, or
process termination. Process summaries exclude command lines, environment
variables, usernames, file contents, tokens, and network destinations.
Detection of GPU hardware is not presented as proof that an application uses a
particular acceleration backend.

## Install

Review all executable skill contents, especially
`scripts/resource_probe.py`, before installation.

Copy the canonical folder to one of these destinations:

| Client and scope | Destination |
| --- | --- |
| Codex project | `.agents/skills/resource-safe-execution` |
| Codex personal | `~/.agents/skills/resource-safe-execution` |
| Claude project | `.claude/skills/resource-safe-execution` |
| Claude personal | `~/.claude/skills/resource-safe-execution` |
| Antigravity workspace | `.agents/skills/resource-safe-execution` |
| Antigravity global | `~/.gemini/config/skills/resource-safe-execution` |

The open [`skills`](https://github.com/vercel-labs/skills) installer can also
copy the package:

```powershell
npx skills add pntech20/resource-safe-execution --skill resource-safe-execution
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

## Run the probe directly

```powershell
python skills/resource-safe-execution/scripts/resource_probe.py --pretty
```

The probe prints one JSON document. Missing host metrics degrade individually
with a machine-readable reason.

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
