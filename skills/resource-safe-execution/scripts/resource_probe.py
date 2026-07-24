#!/usr/bin/env python3
"""Emit a dependency-free, read-only platform snapshot."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone


def snapshot() -> dict[str, str]:
    return {
        "schema_version": "1.0",
        "probe_version": "0.0.1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "platform": platform.system(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    data = snapshot()

    if args.format == "json":
        print(json.dumps(data, sort_keys=True))
        return

    for key, value in data.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
