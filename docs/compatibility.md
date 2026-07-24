# Compatibility

This project separates portable-format evidence, copy-install evidence, and
actual client runtime evidence. Passing one category does not prove another.

## Evidence as of 2026-07-24

| Target | Documented install location | Evidence in this repository | Actual client runtime validation |
| --- | --- | --- | --- |
| Codex project | `.agents/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed |
| Codex personal | `~/.agents/skills/resource-safe-execution` | Path documented from official client guidance | Not performed |
| Claude Code project | `.claude/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed |
| Claude Code personal | `~/.claude/skills/resource-safe-execution` | Path documented from official client guidance | Not performed |
| Antigravity workspace | `.agents/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed |
| Antigravity global | `~/.gemini/config/skills/resource-safe-execution` | Path documented from official client guidance | Not performed |
| Cursor project | `.cursor/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed; no compatibility claim |
| OpenCode project | `.opencode/skills/resource-safe-execution` | Format and install validation by clean-copy tests | Not performed; no compatibility claim |

The copy tests parse the two-field frontmatter and require each direct local
link to resolve inside every copied skill directory. They do not launch any
proprietary client, so this repository currently has no actual client runtime
validation.

## Sources and claim limits

- The portable package contract is based on the
  [Agent Skills specification](https://agentskills.io/specification).
- Codex locations are documented by the official
  [Codex skills guide](https://developers.openai.com/codex/skills).
- Claude locations are documented by the official
  [Claude Code skills guide](https://code.claude.com/docs/en/skills).
- Antigravity locations are documented by the official
  [Antigravity skills guide](https://antigravity.google/docs/skills).
- The optional command-line installation route uses the open
  [`skills` installer](https://github.com/vercel-labs/skills).

These sources support format and location documentation, not a claim that a
specific client version executed this skill successfully. Add runtime evidence
only when it records the client version, operating system, installation method,
test date, and observed result.
