# Compatibility

This project separates portable-format evidence, copy-install evidence, and
actual client runtime evidence. Passing one category does not prove another.

## Evidence as of 2026-07-24

| Target | Documented install location | Evidence in this repository | Actual client runtime validation |
| --- | --- | --- | --- |
| Codex project | `.agents/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed |
| Codex personal | `~/.agents/skills/resource-safe-execution` | Path documented from official client guidance; an earlier candidate was copied to this host's active `C:\Users\Admin\.codex\skills\resource-safe-execution` environment and accepted by the repository validator, but final review did not overwrite that installation | Not performed; installed-path validation is not proof that a client loaded or followed the skill |
| Claude Code project | `.claude/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed |
| Claude Code personal | `~/.claude/skills/resource-safe-execution` | Path documented from official client guidance | Not performed |
| Antigravity workspace | `.agents/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed |
| Antigravity global | `~/.gemini/config/skills/resource-safe-execution` | Path documented from official client guidance | Not performed |
| Cursor project | `.cursor/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed; no compatibility claim |
| OpenCode project | `.opencode/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed; no compatibility claim |

The copy tests verify each hash before copying only the nine regular files in
`skill-manifest.json`, reject symlinks and unexpected ordinary files, then
require the destination paths and hashes to match exactly. They also parse the
two-field frontmatter and require each direct local link to resolve inside every
copied skill directory. They do not launch any proprietary client, so this
repository currently has no actual client runtime validation.

## Platform and release evidence

| Platform | Physical host evidence | Fixture evidence | Hosted CI evidence |
| --- | --- | --- | --- |
| Windows | Physically exercised on this host: the probe emitted valid JSON, process summaries contained no sensitive fields, both validators passed, and the repository suite passed | Windows process and GPU fixtures pass | Workflow configured; hosted run pending |
| macOS | No physical Mac exercised | `vm_stat` and `system_profiler` fixtures pass | Workflow configured; hosted run pending |
| Linux | No physical Linux host exercised | `/proc/stat`, `/proc/meminfo`, and POSIX process fixtures pass | Workflow configured; hosted run pending |

Before final review, the local Codex installation copied 9 tracked canonical
files to `C:\Users\Admin\.codex\skills\resource-safe-execution`. A
relative-path and SHA-256 comparison reported that earlier candidate
byte-identical, and this command exited `0`:

```powershell
python tests/validate_skill.py C:\Users\Admin\.codex\skills\resource-safe-execution
```

Result:

```text
Valid skill: C:\Users\Admin\.codex\skills\resource-safe-execution
```

Final review intentionally did not overwrite that local installation. The
release candidate remains `v0.1.0`. Claude Code, Antigravity, physical macOS,
physical Linux, and every proprietary client runtime check remain unavailable
or unperformed. Hosted macOS and Linux CI must complete before claiming CI
validation; fixtures and a configured workflow are not substitutes for a
completed hosted run.

## Sources and claim limits

- The portable package contract is based on the
  [Agent Skills specification](https://agentskills.io/specification).
- Codex locations are documented by the official
  [Codex skills guide](https://developers.openai.com/codex/skills).
- Claude locations are documented by the official
  [Claude Code skills guide](https://code.claude.com/docs/en/skills).
- Antigravity locations are documented by the official
  [Antigravity skills guide](https://antigravity.google/docs/skills).
- The convenience-only command-line installation route pins the open
  [`skills` installer v1.5.20](https://github.com/vercel-labs/skills/releases/tag/v1.5.20)
  with npm integrity
  `sha512-lPl5KzMfTW+qwHFwc8t6R+wAqmdmSHw1+HWbGdJ/FZYbWLdB34bAZNFWiencM5DVoRaKAgXArmfTWMlNAbl9Gg==`.
  Copy-layout tests do not exercise this remote installer route.

These sources support format and location documentation, not a claim that a
specific client version executed this skill successfully. Add runtime evidence
only when it records the client version, operating system, installation method,
test date, and observed result.
