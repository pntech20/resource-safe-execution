# Contributing

Contributions should keep the canonical package portable, dependency-free at
runtime, and conservative about host control.

1. Add or update tests before every behavioral or parser change. Use
   deterministic fixtures for platform output rather than relying on the
   contributor's current host.
2. Support compatibility claims with evidence that names the client version,
   operating system, installation method, and test date. Format or copy-install
   checks are not client runtime evidence.
3. Keep `skills/resource-safe-execution/SKILL.md` portable. Do not add
   vendor-only canonical syntax; optional vendor metadata belongs outside the
   canonical skill instructions.
4. Run the full local verification suite:

```powershell
python -m compileall skills tests
python -m unittest discover -s tests -v
python tests/validate_skill.py skills/resource-safe-execution
```

Open a focused pull request that explains the safety impact and includes the
verification output. Project releases follow semantic versioning. The JSON
schema version changes only when the probe data contract changes
incompatibly, independent of documentation-only releases.
