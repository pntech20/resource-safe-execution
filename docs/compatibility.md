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
`skill-manifest.json`, reject a symlinked source root and symlinked descendants,
and reject unexpected ordinary files before requiring destination paths and
hashes to match exactly. They do not validate ancestors above the selected source root.
They also parse the two-field frontmatter and require each direct local link to
resolve inside every copied skill directory. They do not launch any proprietary
client, so this repository currently has no actual client runtime validation.

## Platform and release evidence

| Platform | Physical host evidence | Fixture evidence | Hosted CI evidence |
| --- | --- | --- | --- |
| Windows | Physically exercised on this host: the probe emitted valid JSON, process summaries contained no sensitive fields, both validators passed, and the repository suite passed | Windows process and GPU fixtures pass | CI passed on Python 3.10 and 3.13, including the live JSON smoke probe |
| macOS | No physical Mac exercised | `vm_stat` and `system_profiler` fixtures pass | CI passed on Python 3.10 and 3.13, including the live JSON smoke probe |
| Linux | No physical Linux host exercised | `/proc/stat`, `/proc/meminfo`, and POSIX process fixtures pass | CI passed on Python 3.10 and 3.13, including the live JSON smoke probe |

Hosted evidence: [GitHub Actions run 30098155287](https://github.com/pntech20/resource-safe-execution/actions/runs/30098155287), six of six jobs successful.

After final review, the local Codex installation copied the 9 tracked
canonical files to
`C:\Users\Admin\.codex\skills\resource-safe-execution`. Exact relative-path
and SHA-256 comparison against `skill-manifest.json` passed, as did:

```powershell
python tests/validate_skill.py C:\Users\Admin\.codex\skills\resource-safe-execution
```

Result:

```text
Valid skill: C:\Users\Admin\.codex\skills\resource-safe-execution
```

The previous local installation was preserved as a timestamped backup. The
release is `v0.1.0`. Claude Code, Antigravity, physical macOS, physical Linux,
and every proprietary client runtime check remain unavailable or unperformed.
The completed hosted run supports CI-validation claims only; it is not a
substitute for physical-host or proprietary-client evidence.

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
