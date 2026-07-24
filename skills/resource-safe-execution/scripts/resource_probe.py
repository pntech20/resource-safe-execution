#!/usr/bin/env python3
"""Emit a dependency-free, read-only platform resource snapshot."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence


SCHEMA_VERSION = "1.0"
PROBE_VERSION = "0.1.0"
MIN_SAMPLE_SECONDS = 0.1
MAX_SAMPLE_SECONDS = 10.0
SUPPORTED_PLATFORMS = {"Linux", "Darwin", "Windows"}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def run_command(
    args: Sequence[str], timeout_seconds: float = 5.0
) -> CommandResult:
    completed = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
        shell=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def parse_linux_cpu_stat(text: str) -> tuple[int, int]:
    """Return aggregate total and idle ticks from Linux /proc/stat text."""
    aggregate = next(
        (line for line in text.splitlines() if line.split()[:1] == ["cpu"]),
        None,
    )
    if aggregate is None:
        raise ValueError("aggregate CPU row is missing")

    fields = aggregate.split()[1:]
    if len(fields) < 4:
        raise ValueError("aggregate CPU row has too few fields")
    try:
        ticks = [int(field) for field in fields]
    except ValueError as exc:
        raise ValueError("aggregate CPU row contains a non-integer value") from exc
    if any(tick < 0 for tick in ticks):
        raise ValueError("aggregate CPU row contains a negative value")

    idle_ticks = ticks[3] + (ticks[4] if len(ticks) > 4 else 0)
    return sum(ticks), idle_ticks


def calculate_cpu_percent(
    before: tuple[int, int], after: tuple[int, int]
) -> float:
    """Calculate busy CPU percentage from two (total, idle) samples."""
    total_delta = after[0] - before[0]
    idle_delta = after[1] - before[1]
    if total_delta <= 0:
        raise ValueError("CPU total ticks did not increase")
    if idle_delta < 0:
        raise ValueError("CPU idle ticks decreased")
    percent = 100.0 * (total_delta - idle_delta) / total_delta
    return round(min(100.0, max(0.0, percent)), 1)


def parse_linux_meminfo(text: str) -> dict[str, int]:
    """Return total and available memory bytes from Linux /proc/meminfo."""
    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, raw_value = line.split(":", 1)
        parts = raw_value.split()
        if not parts:
            continue
        try:
            value = int(parts[0])
        except ValueError as exc:
            raise ValueError(f"{name} contains a non-integer value") from exc
        multiplier = 1024 if len(parts) > 1 and parts[1].lower() == "kb" else 1
        values[name] = value * multiplier

    if "MemTotal" not in values:
        raise ValueError("MemTotal is missing")
    available = values.get("MemAvailable", values.get("MemFree"))
    if available is None:
        raise ValueError("MemAvailable and MemFree are missing")
    return {
        "total_bytes": values["MemTotal"],
        "available_bytes": available,
    }


def validate_sample_seconds(value: str) -> float:
    """Parse a finite sampling duration within the supported inclusive range."""
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("sample seconds must be a number") from exc
    if not math.isfinite(parsed):
        raise ValueError("sample seconds must be finite")
    if not MIN_SAMPLE_SECONDS <= parsed <= MAX_SAMPLE_SECONDS:
        raise ValueError(
            f"sample seconds must be between {MIN_SAMPLE_SECONDS} and "
            f"{MAX_SAMPLE_SECONDS}"
        )
    return parsed


def _collect_cpu(system: str, sample_seconds: float) -> dict[str, object]:
    result: dict[str, object] = {"logical_cpus": os.cpu_count() or 1}
    if system != "Linux":
        return result

    before_text = Path("/proc/stat").read_text(encoding="utf-8")
    before = parse_linux_cpu_stat(before_text)
    time.sleep(sample_seconds)
    after_text = Path("/proc/stat").read_text(encoding="utf-8")
    after = parse_linux_cpu_stat(after_text)
    result["utilization_percent"] = calculate_cpu_percent(before, after)
    return result


def _collect_memory(system: str) -> dict[str, object]:
    if system != "Linux":
        return {}
    return parse_linux_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8"))


def _collect_disk(working_directory: str | None) -> dict[str, object]:
    resolved = Path(working_directory or os.getcwd()).expanduser().resolve()
    usage = shutil.disk_usage(resolved)
    return {
        "path": str(resolved),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _collect_gpu(system: str) -> dict[str, object]:
    del system
    return {"devices": []}


def _collect_processes(system: str) -> list[dict[str, object]]:
    del system
    return []


def _bounded_reason(error: BaseException) -> str:
    text = str(error).strip() or error.__class__.__name__
    return " ".join(text.split())[:200]


def _unavailable(metric: str, reason: str) -> dict[str, str]:
    return {"metric": metric, "reason": " ".join(reason.split())[:200]}


def _collect_degraded(
    collector: Callable[..., object],
    args: tuple[object, ...],
    metric: str,
    unavailable: list[dict[str, str]],
    fallback: object,
) -> object:
    try:
        return collector(*args)
    except Exception as exc:
        unavailable.append(_unavailable(metric, _bounded_reason(exc)))
        return fallback


def build_recommendation(
    cpu: dict[str, object], memory: dict[str, object]
) -> dict[str, object]:
    """Return conservative worker limits and the balanced default profile."""
    logical_cpus = max(1, int(cpu.get("logical_cpus") or 1))
    worker_limits = {
        "low-impact": max(1, logical_cpus - 2),
        "balanced": max(1, logical_cpus - 1),
        "throughput": max(1, logical_cpus - 1),
    }
    reasons = ["Worker limits reserve logical CPU headroom."]

    total_bytes = memory.get("total_bytes")
    available_bytes = memory.get("available_bytes")
    low_memory = (
        isinstance(total_bytes, (int, float))
        and isinstance(available_bytes, (int, float))
        and total_bytes > 0
        and available_bytes / total_bytes < 0.25
    )
    utilization = cpu.get("utilization_percent")
    cpu_percent = (
        float(utilization)
        if isinstance(utilization, (int, float)) and math.isfinite(utilization)
        else None
    )

    if low_memory or (cpu_percent is not None and cpu_percent >= 90.0):
        worker_limits = {name: 1 for name in worker_limits}
        if low_memory:
            reasons.append("Available memory is below 25 percent; cap workers at 1.")
        if cpu_percent is not None and cpu_percent >= 90.0:
            reasons.append("Sampled CPU is at least 90 percent; cap workers at 1.")
    elif cpu_percent is not None and cpu_percent >= 75.0:
        worker_limits["balanced"] = min(
            worker_limits["balanced"], max(1, logical_cpus // 2)
        )
        reasons.append(
            "Sampled CPU is at least 75 percent; cap balanced workers at half "
            "the logical CPUs."
        )

    return {
        "selected_profile": "balanced",
        "profiles": {
            name: {"max_workers": max_workers}
            for name, max_workers in worker_limits.items()
        },
        "reasons": reasons,
    }


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def collect_snapshot(
    sample_seconds: float = 0.5,
    include_processes: bool = False,
    working_directory: str | None = None,
) -> dict[str, object]:
    """Collect a stable snapshot while degrading failures per metric."""
    system = platform.system()
    if system not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported platform: {system or 'unknown'}")

    unavailable: list[dict[str, str]] = []
    cpu = _collect_degraded(
        _collect_cpu,
        (system, sample_seconds),
        "cpu.utilization_percent",
        unavailable,
        {},
    )
    memory = _collect_degraded(
        _collect_memory,
        (system,),
        "memory.available_bytes",
        unavailable,
        {},
    )
    disk = _collect_degraded(
        _collect_disk,
        (working_directory,),
        "disk.free_bytes",
        unavailable,
        {},
    )
    gpu = _collect_degraded(
        _collect_gpu,
        (system,),
        "gpu.devices",
        unavailable,
        {"devices": []},
    )
    if include_processes:
        processes = _collect_degraded(
            _collect_processes,
            (system,),
            "processes",
            unavailable,
            [],
        )
    else:
        processes = []

    assert isinstance(cpu, dict)
    assert isinstance(memory, dict)
    assert isinstance(disk, dict)
    assert isinstance(gpu, dict)
    assert isinstance(processes, list)

    if "logical_cpus" not in cpu:
        unavailable.append(
            _unavailable("cpu.logical_cpus", "CPU collector did not return a value.")
        )
    if "utilization_percent" not in cpu and not any(
        item["metric"] == "cpu.utilization_percent" for item in unavailable
    ):
        unavailable.append(
            _unavailable(
                "cpu.utilization_percent",
                f"CPU sampling for {system} is not implemented in the core probe.",
            )
        )
    if "total_bytes" not in memory:
        unavailable.append(
            _unavailable(
                "memory.total_bytes",
                f"Memory collection for {system} is not implemented in the core probe.",
            )
        )
    if "available_bytes" not in memory and not any(
        item["metric"] == "memory.available_bytes" for item in unavailable
    ):
        unavailable.append(
            _unavailable(
                "memory.available_bytes",
                f"Memory collection for {system} is not implemented in the core probe.",
            )
        )
    if not gpu.get("devices") and not any(
        item["metric"] == "gpu.devices" for item in unavailable
    ):
        unavailable.append(
            _unavailable(
                "gpu.devices",
                "GPU detection is not implemented in the core probe.",
            )
        )
    if include_processes and not processes and not any(
        item["metric"] == "processes" for item in unavailable
    ):
        unavailable.append(
            _unavailable(
                "processes",
                "Process collection is not implemented in the core probe.",
            )
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "probe_version": PROBE_VERSION,
        "timestamp": _timestamp_utc(),
        "platform": {
            "system": system,
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "gpu": gpu,
        "processes": processes,
        "recommendation": build_recommendation(cpu, memory),
        "warnings": [],
        "unavailable": unavailable,
    }


def render_text(snapshot: dict[str, object]) -> str:
    """Render the stable snapshot as concise human-readable sections."""
    sections = (
        ("Platform", snapshot["platform"]),
        ("CPU", snapshot["cpu"]),
        ("Memory", snapshot["memory"]),
        ("Disk", snapshot["disk"]),
        ("GPU", snapshot["gpu"]),
        ("Processes", snapshot["processes"]),
        ("Recommendation", snapshot["recommendation"]),
        ("Warnings", snapshot["warnings"]),
        ("Unavailable", snapshot["unavailable"]),
    )
    lines = [
        f"Resource snapshot {snapshot['schema_version']} "
        f"(probe {snapshot['probe_version']})",
        f"Timestamp: {snapshot['timestamp']}",
    ]
    for heading, value in sections:
        lines.extend((f"{heading}:", json.dumps(value, ensure_ascii=False, sort_keys=True)))
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--sample-seconds", default="0.5")
    parser.add_argument("--output")
    parser.add_argument("--include-processes", action="store_true")
    parser.add_argument("--working-directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        sample_seconds = validate_sample_seconds(args.sample_seconds)
    except ValueError as exc:
        print(f"Invalid sample duration: {exc}", file=sys.stderr)
        return 2

    system = platform.system()
    if system not in SUPPORTED_PLATFORMS:
        print(
            f"Unsupported platform: {system or 'unknown'}. No metrics were collected.",
            file=sys.stderr,
        )
        return 3

    snapshot = collect_snapshot(
        sample_seconds=sample_seconds,
        include_processes=args.include_processes,
        working_directory=args.working_directory,
    )
    if args.format == "json":
        rendered = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    else:
        rendered = render_text(snapshot)

    if args.output:
        try:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Could not write output file: {_bounded_reason(exc)}", file=sys.stderr)
            return 1
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
