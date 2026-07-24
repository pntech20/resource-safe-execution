"""Dependency-free validation for the canonical two-field skill contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


EXPECTED_FIELDS = {"name", "description"}


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["SKILL.md must start with YAML frontmatter"]
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        return {}, ["SKILL.md frontmatter is not closed"]

    fields: dict[str, str] = {}
    errors: list[str] = []
    for line_number, line in enumerate(lines[1:closing_index], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            errors.append(f"line {line_number}: expected a scalar key: value pair")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key or not value:
            errors.append(f"line {line_number}: key and value must be non-empty")
            continue
        if key in fields:
            errors.append(f"line {line_number}: duplicate field {key!r}")
            continue
        fields[key] = value
    return fields, errors


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_path = skill_dir / "SKILL.md"
    if not skill_dir.is_dir():
        return [f"skill directory does not exist: {skill_dir}"]
    if not skill_path.is_file():
        return [f"SKILL.md does not exist: {skill_path}"]

    fields, parse_errors = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
    errors.extend(parse_errors)
    if set(fields) != EXPECTED_FIELDS:
        errors.append(
            "frontmatter fields must be exactly: "
            + ", ".join(sorted(EXPECTED_FIELDS))
        )
    if fields.get("name") != skill_dir.name:
        errors.append("frontmatter name must match the skill folder")
    description = fields.get("description", "")
    if not 1 <= len(description) <= 1_024:
        errors.append("description must contain 1 to 1024 characters")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", type=Path)
    args = parser.parse_args(argv)
    errors = validate_skill(args.skill_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Valid skill: {args.skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
