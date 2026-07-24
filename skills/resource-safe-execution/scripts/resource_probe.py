#!/usr/bin/env python3
"""Emit a dependency-free snapshot from read-only host inspection."""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import math
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence


SCHEMA_VERSION = "1.0"
PROBE_VERSION = "0.1.0"
MIN_SAMPLE_SECONDS = 0.1
MAX_SAMPLE_SECONDS = 10.0
MAX_COMMAND_TIMEOUT_SECONDS = 5.0
MAX_COMMAND_OUTPUT_BYTES = 1_048_576
SUPPORTED_PLATFORMS = {"Linux", "Darwin", "Windows"}
POSIX_TRUSTED_DIRECTORIES = (
    Path("/bin"),
    Path("/usr/bin"),
    Path("/usr/sbin"),
    Path("/usr/local/bin"),
)
TRUSTED_TOOL_NAMES = {
    "nvidia-smi",
    "pmset",
    "powershell.exe",
    "ps",
    "sysctl",
    "system_profiler",
    "vm_stat",
}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandTimeoutError(RuntimeError):
    """The owned diagnostic child exceeded its bounded runtime."""


class CommandOutputLimitError(RuntimeError):
    """The owned diagnostic child exceeded its combined output allowance."""

    def __init__(self, captured_bytes: int) -> None:
        self.captured_bytes = captured_bytes
        super().__init__(
            f"diagnostic child exceeded the {MAX_COMMAND_OUTPUT_BYTES}-byte "
            "combined output limit"
        )


class CommandStartError(RuntimeError):
    """The diagnostic child could not be started without exposing its path."""


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _current_user_can_write(path: Path) -> bool:
    metadata = path.stat()
    mode = stat.S_IMODE(metadata.st_mode)
    if mode & stat.S_IWOTH:
        return True
    getuid = getattr(os, "geteuid", None)
    getgroups = getattr(os, "getgroups", None)
    getgid = getattr(os, "getegid", None)
    if getuid is None:
        return bool(mode & (stat.S_IWUSR | stat.S_IWGRP))
    user_id = getuid()
    if user_id == 0:
        return bool(mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    if metadata.st_uid == user_id and mode & stat.S_IWUSR:
        return True
    group_ids = set(getgroups() if getgroups is not None else ())
    if getgid is not None:
        group_ids.add(getgid())
    return metadata.st_gid in group_ids and bool(mode & stat.S_IWGRP)


def _regular_non_symlink(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def resolve_trusted_executable(
    name: str,
    *,
    system: str | None = None,
) -> Path:
    """Resolve a known diagnostic tool without consulting cwd or PATH."""
    selected_system = system or platform.system()
    normalized = name.lower()
    if normalized == "powershell":
        normalized = "powershell.exe"
    if normalized == "nvidia-smi.exe":
        normalized = "nvidia-smi"
    if normalized not in TRUSTED_TOOL_NAMES:
        raise FileNotFoundError(
            f"no trusted executable candidate for {name}"
        )

    if selected_system == "Windows":
        system_root_text = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
        program_files_text = os.environ.get("ProgramFiles")
        candidates: list[tuple[Path, Path]] = []
        if system_root_text:
            system_root = Path(system_root_text).expanduser()
            if normalized == "powershell.exe":
                candidates.append(
                    (
                        system_root
                        / "System32"
                        / "WindowsPowerShell"
                        / "v1.0"
                        / "powershell.exe",
                        system_root,
                    )
                )
            elif normalized == "nvidia-smi":
                candidates.append(
                    (
                        system_root / "System32" / "nvidia-smi.exe",
                        system_root,
                    )
                )
        if program_files_text and normalized == "nvidia-smi":
            program_files = Path(program_files_text).expanduser()
            candidates.append(
                (
                    program_files
                    / "NVIDIA Corporation"
                    / "NVSMI"
                    / "nvidia-smi.exe",
                    program_files,
                )
            )

        for candidate, trusted_root in candidates:
            try:
                absolute_candidate = candidate.absolute()
                absolute_root = trusted_root.absolute()
            except OSError:
                continue
            if (
                _is_relative_to(absolute_candidate, absolute_root)
                and _regular_non_symlink(absolute_candidate)
            ):
                return absolute_candidate
        raise FileNotFoundError(
            f"no trusted executable candidate for {name}"
        )

    if selected_system in {"Linux", "Darwin"} and normalized != "powershell.exe":
        for trusted_root in POSIX_TRUSTED_DIRECTORIES:
            candidate = trusted_root / normalized
            try:
                absolute_root = trusted_root.resolve(strict=True)
                absolute_candidate = candidate.resolve(strict=True)
            except OSError:
                continue
            if (
                _is_relative_to(absolute_candidate, absolute_root)
                and _regular_non_symlink(candidate)
                and os.access(candidate, os.X_OK)
                and not _current_user_can_write(candidate)
            ):
                return candidate
    raise FileNotFoundError(f"no trusted executable candidate for {name}")


def _trusted_working_directory() -> Path:
    if platform.system() == "Windows":
        root_text = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
        if root_text:
            system32 = Path(root_text) / "System32"
            if system32.is_dir() and not system32.is_symlink():
                return system32.absolute()
    return Path(os.path.abspath(os.sep))


def _sanitized_environment() -> dict[str, str]:
    environment: dict[str, str] = {}
    if platform.system() == "Windows":
        root_text = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
        if root_text:
            environment["SystemRoot"] = root_text
            environment["WINDIR"] = root_text
    else:
        environment["LANG"] = "C"
        environment["LC_ALL"] = "C"
    return environment


def run_command(
    args: Sequence[str], timeout_seconds: float = 5.0
) -> CommandResult:
    try:
        validated_timeout = float(timeout_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("command timeout must be a number") from exc
    if (
        not math.isfinite(validated_timeout)
        or validated_timeout <= 0
        or validated_timeout > MAX_COMMAND_TIMEOUT_SECONDS
    ):
        raise ValueError(
            f"command timeout must be greater than 0 and at most "
            f"{MAX_COMMAND_TIMEOUT_SECONDS} seconds"
        )

    command = [os.fspath(argument) for argument in args]
    if not command or not Path(command[0]).is_absolute():
        raise ValueError("command must start with an absolute executable path")

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.fspath(_trusted_working_directory()),
            env=_sanitized_environment(),
            shell=False,
            bufsize=0,
        )
    except PermissionError:
        raise CommandStartError(
            "diagnostic child permission denied"
        ) from None
    except OSError:
        raise CommandStartError(
            "diagnostic child could not be started"
        ) from None
    assert process.stdout is not None
    assert process.stderr is not None

    buffers = (bytearray(), bytearray())
    capture_lock = threading.Lock()
    overflow = threading.Event()
    captured_bytes = 0

    def read_bounded(stream: object, output: bytearray) -> None:
        nonlocal captured_bytes
        while not overflow.is_set():
            chunk = stream.read(65_536)
            if not chunk:
                return
            with capture_lock:
                remaining = MAX_COMMAND_OUTPUT_BYTES - captured_bytes
                accepted = min(len(chunk), max(0, remaining))
                if accepted:
                    output.extend(chunk[:accepted])
                    captured_bytes += accepted
                if accepted < len(chunk):
                    overflow.set()
                    return

    readers = (
        threading.Thread(
            target=read_bounded,
            args=(process.stdout, buffers[0]),
            daemon=True,
        ),
        threading.Thread(
            target=read_bounded,
            args=(process.stderr, buffers[1]),
            daemon=True,
        ),
    )
    for reader in readers:
        reader.start()

    deadline = time.monotonic() + validated_timeout
    breach: str | None = None
    while process.poll() is None:
        if overflow.is_set():
            breach = "overflow"
            break
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            breach = "timeout"
            break
        overflow.wait(min(0.01, remaining_seconds))

    if breach is not None and process.poll() is None:
        process.kill()
    returncode = process.wait()
    for reader in readers:
        reader.join()
    process.stdout.close()
    process.stderr.close()

    if overflow.is_set():
        raise CommandOutputLimitError(captured_bytes)
    if breach == "timeout":
        raise CommandTimeoutError(
            f"diagnostic child timed out after {validated_timeout:g} seconds"
        )
    return CommandResult(
        returncode,
        bytes(buffers[0]).decode("utf-8", errors="replace"),
        bytes(buffers[1]).decode("utf-8", errors="replace"),
    )


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
    return sum(ticks[:8]), idle_ticks


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


def parse_nvidia_smi(text: str) -> list[dict[str, object]]:
    """Parse the bounded NVIDIA CSV query as driver and device evidence."""
    devices: list[dict[str, object]] = []
    for row in csv.reader(text.splitlines()):
        if len(row) != 6:
            continue
        try:
            index = int(row[0].strip())
            name = row[1].strip()
            driver_version = row[2].strip()
            memory_total_mib = int(row[3].strip())
            memory_used_mib = int(row[4].strip())
            utilization_percent = float(row[5].strip())
        except ValueError:
            continue
        if (
            index < 0
            or not name
            or not driver_version
            or memory_total_mib < 0
            or memory_used_mib < 0
            or not math.isfinite(utilization_percent)
        ):
            continue
        devices.append(
            {
                "index": index,
                "name": name,
                "driver_version": driver_version,
                "memory_total_mib": memory_total_mib,
                "memory_used_mib": memory_used_mib,
                "utilization_percent": utilization_percent,
            }
        )
    return devices


def parse_macos_vm_stat(text: str) -> dict[str, int]:
    """Parse vm_stat and count immediately reusable pages as available."""
    page_size_match = re.search(r"page size of\s+(\d+)\s+bytes", text)
    if page_size_match is None:
        raise ValueError("vm_stat page size is missing")
    page_size = int(page_size_match.group(1))
    pages: dict[str, int] = {}
    for line in text.splitlines():
        match = re.match(r"\s*([^:]+):\s*(\d+)\.?\s*$", line)
        if match:
            pages[match.group(1).strip()] = int(match.group(2))
    available_names = ("Pages free", "Pages inactive", "Pages speculative")
    if not any(name in pages for name in available_names):
        raise ValueError("vm_stat available page counters are missing")
    available_pages = sum(pages.get(name, 0) for name in available_names)
    return {"available_bytes": available_pages * page_size}


def _vendor_name(*values: object) -> str:
    evidence = " ".join(str(value) for value in values if value).lower()
    if "nvidia" in evidence:
        return "NVIDIA"
    if "advanced micro devices" in evidence or "amd" in evidence or "radeon" in evidence:
        return "AMD"
    if "intel" in evidence:
        return "Intel"
    if "apple" in evidence:
        return "Apple"
    return "unknown"


def _memory_label_bytes(value: object) -> int | None:
    if not isinstance(value, str) or "shared" in value.lower():
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB|KB)", value, re.IGNORECASE)
    if match is None:
        return None
    multipliers = {"kb": 1024, "mb": 1024**2, "gb": 1024**3}
    return int(float(match.group(1)) * multipliers[match.group(2).lower()])


def _graphics_device(
    *,
    name: str,
    vendor: str,
    memory_bytes: int | None,
    driver_version: str | None,
    detection_source: str,
    backend_name: str,
) -> dict[str, object]:
    return {
        "name": name,
        "vendor": vendor,
        "memory_bytes": memory_bytes,
        "driver_version": driver_version,
        "detection_source": detection_source,
        "backend_claims": [
            {
                "name": backend_name,
                "verified_for_application": False,
            }
        ],
    }


def parse_macos_displays(text: str) -> list[dict[str, object]]:
    """Normalize system_profiler display JSON without claiming app support."""
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("system_profiler display JSON must be an object")
    raw_devices = payload.get("SPDisplaysDataType", [])
    if isinstance(raw_devices, dict):
        raw_devices = [raw_devices]
    if not isinstance(raw_devices, list):
        raise ValueError("system_profiler display list is malformed")

    devices: list[dict[str, object]] = []
    for raw in raw_devices:
        if not isinstance(raw, dict):
            continue
        raw_name = raw.get("sppci_model") or raw.get("_name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        vendor_evidence = raw.get("sppci_vendor") or raw.get("spdisplays_vendor")
        memory = _memory_label_bytes(
            raw.get("spdisplays_vram") or raw.get("spdisplays_vram_shared")
        )
        driver = raw.get("spdisplays_gmux-version")
        devices.append(
            _graphics_device(
                name=raw_name.strip(),
                vendor=_vendor_name(vendor_evidence, raw_name),
                memory_bytes=memory,
                driver_version=driver.strip() if isinstance(driver, str) else None,
                detection_source="system_profiler",
                backend_name="metal-device",
            )
        )
    return devices


def _json_records(text: str, source: str) -> list[dict[str, object]]:
    if not text.strip():
        return []
    payload = json.loads(text)
    if isinstance(payload, dict):
        return [payload]
    if not isinstance(payload, list):
        raise ValueError(f"{source} JSON must be an object or array")
    return [record for record in payload if isinstance(record, dict)]


def parse_windows_gpu(text: str) -> list[dict[str, object]]:
    """Normalize one-or-many Win32_VideoController JSON records."""
    devices: list[dict[str, object]] = []
    for raw in _json_records(text, "Windows GPU"):
        name = raw.get("Name")
        if not isinstance(name, str) or not name.strip():
            continue
        raw_memory = raw.get("AdapterRAM")
        memory_bytes = (
            int(raw_memory)
            if isinstance(raw_memory, (int, float))
            and not isinstance(raw_memory, bool)
            and math.isfinite(raw_memory)
            and raw_memory >= 0
            else None
        )
        raw_driver = raw.get("DriverVersion")
        driver_version = (
            raw_driver.strip()
            if isinstance(raw_driver, str) and raw_driver.strip()
            else None
        )
        devices.append(
            _graphics_device(
                name=name.strip(),
                vendor=_vendor_name(raw.get("AdapterCompatibility"), name),
                memory_bytes=memory_bytes,
                driver_version=driver_version,
                detection_source="windows-cim",
                backend_name="graphics-device",
            )
        )
    return devices


def parse_posix_processes(
    text: str, limit: int = 5
) -> list[dict[str, object]]:
    """Parse ps output while retaining only the privacy-preserving fields."""
    processes: list[dict[str, object]] = []
    for line in text.splitlines():
        fields = line.strip().split(maxsplit=3)
        if len(fields) != 4:
            continue
        try:
            pid = int(fields[0])
            cpu_percent = float(fields[1])
            memory_kib = int(fields[2])
        except ValueError:
            continue
        name = fields[3].strip()
        if (
            pid <= 0
            or not name
            or memory_kib < 0
            or not math.isfinite(cpu_percent)
            or cpu_percent < 0
        ):
            continue
        processes.append(
            {
                "pid": pid,
                "name": name,
                "cpu_percent": cpu_percent,
                "memory_bytes": memory_kib * 1024,
            }
        )
    processes.sort(
        key=lambda item: (
            -float(item["cpu_percent"]),
            -int(item["memory_bytes"]),
            int(item["pid"]),
        )
    )
    return processes[: max(0, int(limit))]


def parse_windows_processes(
    text: str, limit: int = 5
) -> list[dict[str, object]]:
    """Parse CIM process JSON while retaining only four approved fields."""
    processes: list[dict[str, object]] = []
    for raw in _json_records(text, "Windows process"):
        try:
            pid = int(raw.get("IDProcess"))
            cpu_percent = float(raw.get("PercentProcessorTime"))
            memory_bytes = int(raw.get("WorkingSetPrivate"))
        except (TypeError, ValueError):
            continue
        raw_name = raw.get("Name")
        name = raw_name.strip() if isinstance(raw_name, str) else ""
        if (
            pid <= 0
            or not name
            or name.lower() in {"_total", "idle"}
            or memory_bytes < 0
            or not math.isfinite(cpu_percent)
            or cpu_percent < 0
        ):
            continue
        processes.append(
            {
                "pid": pid,
                "name": name,
                "cpu_percent": cpu_percent,
                "memory_bytes": memory_bytes,
            }
        )
    processes.sort(
        key=lambda item: (
            -float(item["cpu_percent"]),
            -int(item["memory_bytes"]),
            int(item["pid"]),
        )
    )
    return processes[: max(0, int(limit))]


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


def _checked_stdout(
    args: Sequence[str],
    *,
    system: str | None = None,
    executable: Path | None = None,
    allow_empty: bool = False,
) -> str:
    if not args:
        raise ValueError("diagnostic command is empty")
    tool_name = Path(args[0]).name
    resolved = executable or resolve_trusted_executable(
        tool_name,
        system=system,
    )
    result = run_command(
        [os.fspath(resolved), *args[1:]],
        timeout_seconds=5.0,
    )
    if result.returncode != 0:
        error_text = result.stderr.lower()
        if "permission denied" in error_text or "access is denied" in error_text:
            raise PermissionError(f"{tool_name} permission denied")
        raise RuntimeError(f"{tool_name} exited with status {result.returncode}")
    if not allow_empty and not result.stdout.strip():
        raise ValueError(f"{tool_name} returned no data")
    return result.stdout


def _windows_cpu_times() -> tuple[int, int]:
    class FileTime(ctypes.Structure):
        _fields_ = (("low", ctypes.c_uint32), ("high", ctypes.c_uint32))

    def value(file_time: FileTime) -> int:
        return (int(file_time.high) << 32) | int(file_time.low)

    idle = FileTime()
    kernel = FileTime()
    user = FileTime()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return value(kernel) + value(user), value(idle)


def _windows_memory_status() -> tuple[int, int]:
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = (
            ("length", ctypes.c_uint32),
            ("memory_load", ctypes.c_uint32),
            ("total_physical", ctypes.c_uint64),
            ("available_physical", ctypes.c_uint64),
            ("total_page_file", ctypes.c_uint64),
            ("available_page_file", ctypes.c_uint64),
            ("total_virtual", ctypes.c_uint64),
            ("available_virtual", ctypes.c_uint64),
            ("available_extended_virtual", ctypes.c_uint64),
        )

    status = MemoryStatusEx()
    status.length = ctypes.sizeof(status)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(status.total_physical), int(status.available_physical)


def _collect_cpu(
    system: str,
    sample_seconds: float,
    unavailable: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    logical_cpus = os.cpu_count() or 1
    result: dict[str, object] = {"logical_cpus": logical_cpus}
    try:
        if system == "Linux":
            before = parse_linux_cpu_stat(
                Path("/proc/stat").read_text(encoding="utf-8")
            )
            time.sleep(sample_seconds)
            after = parse_linux_cpu_stat(
                Path("/proc/stat").read_text(encoding="utf-8")
            )
            result["utilization_percent"] = calculate_cpu_percent(before, after)
        elif system == "Windows":
            before = _windows_cpu_times()
            time.sleep(sample_seconds)
            after = _windows_cpu_times()
            result["utilization_percent"] = calculate_cpu_percent(before, after)
        elif system == "Darwin":
            samples = []
            for sample_index in range(2):
                output = _checked_stdout(
                    ["ps", "-A", "-o", "%cpu="],
                    system=system,
                )
                values = []
                for raw_value in output.splitlines():
                    try:
                        value = float(raw_value.strip())
                    except ValueError:
                        continue
                    if math.isfinite(value) and value >= 0:
                        values.append(value)
                if not values:
                    raise ValueError("ps returned no CPU percentages")
                samples.append(sum(values))
                if sample_index == 0:
                    time.sleep(sample_seconds)
            result["utilization_percent"] = round(
                min(100.0, max(0.0, sum(samples) / len(samples) / logical_cpus)),
                1,
            )
    except Exception as exc:
        if unavailable is not None:
            unavailable.append(
                _unavailable("cpu.utilization_percent", _bounded_reason(exc))
            )

    if system in {"Linux", "Darwin"}:
        try:
            getloadavg = getattr(os, "getloadavg")
            load_average = tuple(float(value) for value in getloadavg())
            if (
                len(load_average) != 3
                or any(
                    not math.isfinite(value) or value < 0
                    for value in load_average
                )
            ):
                raise ValueError("load average returned malformed values")
            result["load_average"] = {
                "1m": load_average[0],
                "5m": load_average[1],
                "15m": load_average[2],
            }
        except Exception as exc:
            if unavailable is not None:
                unavailable.append(
                    _unavailable("cpu.load_average", _bounded_reason(exc))
                )
    elif system == "Windows" and unavailable is not None:
        unavailable.append(
            _unavailable(
                "cpu.load_average",
                "load average is unsupported on Windows",
            )
        )
    return result


def _collect_memory(
    system: str,
    unavailable: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    if system == "Linux":
        return parse_linux_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8"))
    if system == "Windows":
        total_bytes, available_bytes = _windows_memory_status()
        return {
            "total_bytes": total_bytes,
            "available_bytes": available_bytes,
        }
    if system == "Darwin":
        try:
            total_text = _checked_stdout(
                ["sysctl", "-n", "hw.memsize"],
                system=system,
            )
            try:
                total_bytes = int(total_text.strip())
            except ValueError as exc:
                raise ValueError("sysctl hw.memsize is not an integer") from exc
        except Exception as exc:
            if unavailable is not None:
                unavailable.append(
                    _unavailable("memory.total_bytes", _bounded_reason(exc))
                )
            memory: dict[str, object] = {}
        else:
            memory = {"total_bytes": total_bytes}
        try:
            memory.update(
                parse_macos_vm_stat(
                    _checked_stdout(["vm_stat"], system=system)
                )
            )
        except Exception as exc:
            if unavailable is not None:
                unavailable.append(
                    _unavailable("memory.available_bytes", _bounded_reason(exc))
                )
        return memory
    return {}


def _collect_disk(working_directory: str | None) -> dict[str, object]:
    resolved = Path(working_directory or os.getcwd()).expanduser().resolve()
    usage = shutil.disk_usage(resolved)
    return {
        "path": str(resolved),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _linux_gpu_devices() -> list[dict[str, object]]:
    devices: list[dict[str, object]] = []
    vendor_ids = {
        "0x10de": "NVIDIA",
        "0x1002": "AMD",
        "0x8086": "Intel",
    }
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]*")):
        device_path = card / "device"
        vendor_path = device_path / "vendor"
        if not vendor_path.is_file():
            continue
        vendor_id = vendor_path.read_text(encoding="utf-8").strip().lower()
        vendor = vendor_ids.get(vendor_id, "unknown")
        device_id_path = device_path / "device"
        device_id = (
            device_id_path.read_text(encoding="utf-8").strip()
            if device_id_path.is_file()
            else "unknown"
        )
        devices.append(
            _graphics_device(
                name=f"{vendor} graphics device {device_id}",
                vendor=vendor,
                memory_bytes=None,
                driver_version=None,
                detection_source="linux-sysfs",
                backend_name="graphics-device",
            )
        )
    return devices


def _base_gpu_devices(system: str) -> list[dict[str, object]]:
    if system == "Windows":
        output = _checked_stdout(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name,AdapterRAM,DriverVersion,"
                "AdapterCompatibility | ConvertTo-Json -Compress",
            ],
            system=system,
            allow_empty=True,
        )
        return parse_windows_gpu(output)
    if system == "Darwin":
        return parse_macos_displays(
            _checked_stdout(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                system=system,
            )
        )
    if system == "Linux":
        return _linux_gpu_devices()
    return []


def _nvidia_devices(executable: Path) -> list[dict[str, object]]:
    output = _checked_stdout(
        [
            "nvidia-smi",
            "--query-gpu=index,name,driver_version,memory.total,memory.used,"
            "utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        executable=executable,
        allow_empty=True,
    )
    devices = []
    for raw in parse_nvidia_smi(output):
        normalized = _graphics_device(
            name=str(raw["name"]),
            vendor="NVIDIA",
            memory_bytes=int(raw["memory_total_mib"]) * 1024**2,
            driver_version=str(raw["driver_version"]),
            detection_source="nvidia-smi",
            backend_name="cuda-driver",
        )
        normalized.update(raw)
        devices.append(normalized)
    if output.strip() and not devices:
        raise ValueError("nvidia-smi returned no valid device rows")
    return devices


def _collect_gpu(
    system: str,
    unavailable: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    try:
        devices = _base_gpu_devices(system)
    except Exception as exc:
        devices = []
        if unavailable is not None:
            unavailable.append(
                _unavailable("gpu.base", _bounded_reason(exc))
            )

    try:
        nvidia_executable = resolve_trusted_executable(
            "nvidia-smi",
            system=system,
        )
        nvidia_devices = _nvidia_devices(nvidia_executable)
    except Exception as exc:
        if unavailable is not None:
            unavailable.append(
                _unavailable("gpu.nvidia", _bounded_reason(exc))
            )
    else:
        if nvidia_devices:
            devices = [
                device for device in devices if device.get("vendor") != "NVIDIA"
            ]
            devices.extend(nvidia_devices)
    return {"devices": devices}


def _collect_processes(system: str) -> list[dict[str, object]]:
    if system == "Windows":
        output = _checked_stdout(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance "
                "Win32_PerfFormattedData_PerfProc_Process | "
                "Select-Object IDProcess,Name,PercentProcessorTime,"
                "WorkingSetPrivate | ConvertTo-Json -Compress",
            ],
            system=system,
        )
        return parse_windows_processes(output)
    if system in {"Linux", "Darwin"}:
        return parse_posix_processes(
            _checked_stdout(
                ["ps", "-axo", "pid=,pcpu=,rss=,comm="],
                system=system,
            )
        )
    return []


def _collect_power(system: str) -> dict[str, object]:
    if system == "Darwin":
        output = _checked_stdout(["pmset", "-g", "batt"], system=system)
        result: dict[str, object] = {"detection_source": "pmset"}
        source_match = re.search(r"Now drawing from '([^']+)'", output)
        percent_match = re.search(r"(\d+)%", output)
        if source_match:
            result["source"] = source_match.group(1)
        if percent_match:
            result["battery_percent"] = int(percent_match.group(1))
        return result
    if system == "Linux":
        supplies = Path("/sys/class/power_supply")
        if not supplies.is_dir():
            return {}
        for supply in sorted(supplies.iterdir()):
            type_path = supply / "type"
            if not type_path.is_file():
                continue
            supply_type = type_path.read_text(encoding="utf-8").strip()
            if supply_type != "Battery":
                continue
            result = {
                "detection_source": "linux-sysfs",
                "source": supply_type,
            }
            capacity_path = supply / "capacity"
            status_path = supply / "status"
            if capacity_path.is_file():
                result["battery_percent"] = int(
                    capacity_path.read_text(encoding="utf-8").strip()
                )
            if status_path.is_file():
                result["status"] = status_path.read_text(
                    encoding="utf-8"
                ).strip()
            return result
    return {}


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
    """Return conservative worker limits and the selected profile."""
    logical_cpus = max(1, int(cpu.get("logical_cpus") or 1))
    worker_limits = {
        "low-impact": max(0, logical_cpus - 2),
        "balanced": max(0, logical_cpus - 1),
        "throughput": max(0, logical_cpus - 1),
    }
    reasons = ["Worker limits reserve logical CPU headroom."]
    selected_profile = "balanced"

    total_bytes = memory.get("total_bytes")
    available_bytes = memory.get("available_bytes")
    memory_known = (
        isinstance(total_bytes, (int, float))
        and isinstance(available_bytes, (int, float))
        and not isinstance(total_bytes, bool)
        and not isinstance(available_bytes, bool)
        and math.isfinite(total_bytes)
        and math.isfinite(available_bytes)
        and total_bytes > 0
        and available_bytes >= 0
    )
    low_memory = (
        memory_known and available_bytes / total_bytes < 0.25
    )
    utilization = cpu.get("utilization_percent")
    cpu_percent = (
        float(utilization)
        if (
            isinstance(utilization, (int, float))
            and not isinstance(utilization, bool)
            and math.isfinite(utilization)
        )
        else None
    )

    if not memory_known or cpu_percent is None:
        worker_limits = {
            name: min(max_workers, 1)
            for name, max_workers in worker_limits.items()
        }
        selected_profile = "low-impact"
        if not memory_known:
            reasons.append(
                "Memory availability is unknown; cap workers at 1."
            )
        if cpu_percent is None:
            reasons.append(
                "Sampled CPU utilization is unknown; cap workers at 1."
            )
    elif low_memory or cpu_percent >= 90.0:
        worker_limits = {
            name: min(max_workers, 1)
            for name, max_workers in worker_limits.items()
        }
        selected_profile = "low-impact"
        if low_memory:
            reasons.append("Available memory is below 25 percent; cap workers at 1.")
        if cpu_percent >= 90.0:
            reasons.append("Sampled CPU is at least 90 percent; cap workers at 1.")
    elif cpu_percent >= 75.0:
        worker_limits["balanced"] = min(
            worker_limits["balanced"], logical_cpus // 2
        )
        selected_profile = "low-impact"
        reasons.append(
            "Sampled CPU is at least 75 percent; cap balanced workers at half "
            "the logical CPUs."
        )

    return {
        "selected_profile": selected_profile,
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
    validated_sample_seconds = validate_sample_seconds(str(sample_seconds))
    system = platform.system()
    if system not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported platform: {system or 'unknown'}")

    unavailable: list[dict[str, str]] = []
    cpu = _collect_degraded(
        _collect_cpu,
        (system, validated_sample_seconds, unavailable),
        "cpu.utilization_percent",
        unavailable,
        {},
    )
    memory = _collect_degraded(
        _collect_memory,
        (system, unavailable),
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
        (system, unavailable),
        "gpu.devices",
        unavailable,
        {"devices": []},
    )
    power = _collect_degraded(
        _collect_power,
        (system,),
        "platform.power",
        unavailable,
        {},
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
    assert isinstance(power, dict)
    assert isinstance(processes, list)

    cpu_failure_reason = next(
        (
            item["reason"]
            for item in unavailable
            if item["metric"] == "cpu.utilization_percent"
        ),
        "CPU collector did not return a value.",
    )
    if "logical_cpus" not in cpu and not any(
        item["metric"] == "cpu.logical_cpus" for item in unavailable
    ):
        unavailable.append(
            _unavailable("cpu.logical_cpus", cpu_failure_reason)
        )
    if "utilization_percent" not in cpu and not any(
        item["metric"] == "cpu.utilization_percent" for item in unavailable
    ):
        unavailable.append(
            _unavailable(
                "cpu.utilization_percent",
                "CPU sampler did not return a value.",
            )
        )
    if "load_average" not in cpu and not any(
        item["metric"] == "cpu.load_average" for item in unavailable
    ):
        unavailable.append(
            _unavailable("cpu.load_average", cpu_failure_reason)
        )
    memory_failure_reason = next(
        (
            item["reason"]
            for item in unavailable
            if item["metric"].startswith("memory.")
        ),
        "Memory collector did not return a value.",
    )
    if "total_bytes" not in memory and not any(
        item["metric"] == "memory.total_bytes" for item in unavailable
    ):
        unavailable.append(
            _unavailable("memory.total_bytes", memory_failure_reason)
        )
    if "available_bytes" not in memory and not any(
        item["metric"] == "memory.available_bytes" for item in unavailable
    ):
        unavailable.append(
            _unavailable(
                "memory.available_bytes",
                memory_failure_reason,
            )
        )
    disk_failure_reason = next(
        (
            item["reason"]
            for item in unavailable
            if item["metric"] == "disk.free_bytes"
        ),
        "Disk collector did not return a value.",
    )
    for disk_field in ("total_bytes", "used_bytes", "free_bytes"):
        metric = f"disk.{disk_field}"
        if disk_field not in disk and not any(
            item["metric"] == metric for item in unavailable
        ):
            unavailable.append(_unavailable(metric, disk_failure_reason))
    platform_snapshot: dict[str, object] = {
        "system": system,
        "release": platform.release(),
        "machine": platform.machine(),
    }
    if power:
        platform_snapshot["power"] = power

    return {
        "schema_version": SCHEMA_VERSION,
        "probe_version": PROBE_VERSION,
        "timestamp": _timestamp_utc(),
        "platform": platform_snapshot,
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


def _write_output_exclusive(path_text: str, content: str) -> None:
    destination = Path(path_text).expanduser().absolute()
    if destination.is_symlink():
        raise FileExistsError("output destination is a symlink")
    if destination.exists():
        raise FileExistsError("output destination already exists")

    parent = destination.parent
    current = parent
    while True:
        if current.is_symlink():
            raise OSError("output parent path contains a symlink")
        if current == current.parent:
            break
        current = current.parent
    if not parent.is_dir():
        raise OSError("output parent is not an existing regular directory")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(destination, flags, 0o600)
    with os.fdopen(
        descriptor,
        "w",
        encoding="utf-8",
        newline="",
    ) as output:
        output.write(content)


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
            _write_output_exclusive(args.output, rendered + "\n")
        except OSError as exc:
            print(f"Could not write output file: {_bounded_reason(exc)}", file=sys.stderr)
            return 1
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
