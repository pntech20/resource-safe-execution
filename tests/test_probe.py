import contextlib
import importlib.util
import inspect
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = (
    REPO_ROOT / "skills" / "resource-safe-execution" / "scripts" / "resource_probe.py"
)
FIXTURES = REPO_ROOT / "tests" / "fixtures"

spec = importlib.util.spec_from_file_location("resource_probe_under_test", PROBE_PATH)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


REQUIRED_KEYS = {
    "schema_version",
    "probe_version",
    "timestamp",
    "platform",
    "cpu",
    "memory",
    "disk",
    "gpu",
    "processes",
    "recommendation",
    "warnings",
    "unavailable",
}


def sample_snapshot() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "probe_version": "0.1.0",
        "timestamp": "2026-07-24T00:00:00Z",
        "platform": {"system": "Linux", "machine": "x86_64"},
        "cpu": {"logical_cpus": 8, "utilization_percent": 25.0},
        "memory": {
            "total_bytes": 16_777_216,
            "available_bytes": 8_388_608,
        },
        "disk": {"total_bytes": 1000, "free_bytes": 500},
        "gpu": {"devices": []},
        "processes": [],
        "recommendation": {
            "selected_profile": "balanced",
            "profiles": {"balanced": {"max_workers": 7}},
            "reasons": ["Capacity is available."],
        },
        "warnings": [],
        "unavailable": [],
    }


class LinuxParserTests(unittest.TestCase):
    def test_parse_linux_cpu_stat_returns_total_and_idle_ticks(self) -> None:
        text = (FIXTURES / "linux-proc-stat-before.txt").read_text(encoding="utf-8")
        self.assertEqual((1000, 850), probe.parse_linux_cpu_stat(text))
        self.assertEqual(
            (1000, 850),
            probe.parse_linux_cpu_stat("cpu  100 0 50 850 0 0 0 0 0 0\n"),
        )

    def test_parse_linux_cpu_stat_does_not_double_count_guest_ticks(self) -> None:
        text = (FIXTURES / "linux-proc-stat-guests.txt").read_text(encoding="utf-8")
        self.assertEqual((1040, 855), probe.parse_linux_cpu_stat(text))

    def test_calculate_cpu_percent_uses_tick_deltas(self) -> None:
        self.assertEqual(50.0, probe.calculate_cpu_percent((1000, 850), (1100, 900)))

    def test_parse_linux_meminfo_converts_kibibytes_to_bytes(self) -> None:
        text = (FIXTURES / "linux-meminfo.txt").read_text(encoding="utf-8")
        parsed = probe.parse_linux_meminfo(text)
        self.assertEqual(16_384 * 1024, parsed["total_bytes"])
        self.assertEqual(8_192 * 1024, parsed["available_bytes"])


class PlatformParserTests(unittest.TestCase):
    def test_parse_nvidia_smi_preserves_driver_device_and_utilization_fields(
        self,
    ) -> None:
        text = (FIXTURES / "nvidia-smi.csv").read_text(encoding="utf-8")
        devices = probe.parse_nvidia_smi(text)
        self.assertEqual(2, len(devices))
        self.assertEqual(
            {
                "index": 0,
                "name": "NVIDIA GeForce RTX 4090",
                "driver_version": "555.85",
                "memory_total_mib": 24564,
                "memory_used_mib": 1024,
                "utilization_percent": 12.0,
            },
            devices[0],
        )
        self.assertEqual("NVIDIA RTX™ A6000", devices[1]["name"])

    def test_parse_macos_vm_stat_calculates_available_bytes(self) -> None:
        text = (FIXTURES / "macos-vm-stat.txt").read_text(encoding="utf-8")
        self.assertEqual(
            {"available_bytes": (100 + 200 + 10) * 16_384},
            probe.parse_macos_vm_stat(text),
        )

    def test_parse_macos_displays_normalizes_shared_and_dedicated_devices(
        self,
    ) -> None:
        text = (FIXTURES / "macos-system-profiler.json").read_text(encoding="utf-8")
        devices = probe.parse_macos_displays(text)
        self.assertEqual(2, len(devices))
        self.assertEqual("Apple", devices[0]["vendor"])
        self.assertIsNone(devices[0]["memory_bytes"])
        self.assertEqual(8 * 1024**3, devices[1]["memory_bytes"])
        self.assert_gpu_contract(devices)

    def test_parse_macos_displays_distinguishes_empty_from_malformed_records(
        self,
    ) -> None:
        self.assertEqual(
            [],
            probe.parse_macos_displays('{"SPDisplaysDataType": []}'),
        )
        malformed_payloads = (
            '{"SPDisplaysDataType": [{}]}',
            '{"SPDisplaysDataType": [42]}',
            '{"SPDisplaysDataType": [{"sppci_model": "   "}]}',
        )
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "display record"):
                    probe.parse_macos_displays(payload)

    def test_parse_macos_displays_rejects_missing_source_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "SPDisplaysDataType"):
            probe.parse_macos_displays("{}")

    def test_parse_windows_gpu_accepts_array_and_single_object_json(self) -> None:
        text = (FIXTURES / "windows-gpu.json").read_text(encoding="utf-8")
        devices = probe.parse_windows_gpu(text)
        self.assertEqual(2, len(devices))
        self.assertEqual(4_293_918_720, devices[0]["memory_bytes"])
        self.assertEqual("Intel", devices[1]["vendor"])
        self.assertEqual("Intel® Arc™ Graphics", devices[1]["name"])
        single = probe.parse_windows_gpu(
            json.dumps(
                {
                    "Name": "AMD Radeon RX 7900 XTX",
                    "AdapterRAM": 24_000_000_000,
                    "DriverVersion": "31.0",
                    "AdapterCompatibility": "Advanced Micro Devices",
                }
            )
        )
        self.assertEqual(1, len(single))
        self.assertEqual("AMD", single[0]["vendor"])
        self.assert_gpu_contract(devices + single)

    def test_parse_windows_gpu_distinguishes_empty_from_malformed_records(
        self,
    ) -> None:
        for payload in ("", "[]"):
            with self.subTest(payload=payload):
                self.assertEqual([], probe.parse_windows_gpu(payload))
        malformed_payloads = (
            "[{}]",
            "[42]",
            '[{"Name": "   "}]',
        )
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "GPU record"):
                    probe.parse_windows_gpu(payload)

    def assert_gpu_contract(self, devices: list[dict[str, object]]) -> None:
        required = {
            "name",
            "vendor",
            "memory_bytes",
            "driver_version",
            "detection_source",
            "backend_claims",
        }
        for device in devices:
            self.assertTrue(required.issubset(device))
            claims = device["backend_claims"]
            self.assertTrue(claims)
            self.assertTrue(
                all(claim["verified_for_application"] is False for claim in claims)
            )


class ProcessParserTests(unittest.TestCase):
    ALLOWED_KEYS = {"pid", "name", "cpu_percent", "memory_bytes"}

    def test_parse_posix_processes_ignores_malformed_rows_and_limits_output(
        self,
    ) -> None:
        text = (FIXTURES / "processes-posix.txt").read_text(encoding="utf-8")
        processes = probe.parse_posix_processes(text, limit=1)
        self.assertEqual(
            [
                {
                    "pid": 101,
                    "name": "python3",
                    "cpu_percent": 12.5,
                    "memory_bytes": 2048 * 1024,
                }
            ],
            processes,
        )
        self.assertEqual(self.ALLOWED_KEYS, set(processes[0]))

    def test_parse_windows_processes_handles_array_and_single_object(self) -> None:
        text = (FIXTURES / "processes-windows.json").read_text(encoding="utf-8")
        processes = probe.parse_windows_processes(text)
        self.assertEqual(2, len(processes))
        self.assertEqual("Rendérér", processes[1]["name"])
        single = probe.parse_windows_processes(
            json.dumps(
                {
                    "IDProcess": 404,
                    "Name": "single",
                    "PercentProcessorTime": 1,
                    "WorkingSetPrivate": 4096,
                }
            )
        )
        self.assertEqual(404, single[0]["pid"])
        for process in processes + single:
            self.assertEqual(self.ALLOWED_KEYS, set(process))


class PlatformCollectorTests(unittest.TestCase):
    def test_macos_cpu_averages_two_ps_samples_per_logical_cpu(self) -> None:
        samples = (
            probe.CommandResult(0, "80.0\n80.0\n", ""),
            probe.CommandResult(0, "160.0\n160.0\n", ""),
        )
        with (
            mock.patch.object(probe, "run_command", side_effect=samples),
            mock.patch.object(
                probe,
                "resolve_trusted_executable",
                return_value=Path("/usr/bin/ps"),
                create=True,
            ),
            mock.patch.object(probe.os, "cpu_count", return_value=8),
            mock.patch.object(
                probe.os,
                "getloadavg",
                return_value=(1.0, 2.0, 3.0),
                create=True,
            ),
            mock.patch.object(probe.time, "sleep"),
        ):
            result = probe._collect_cpu("Darwin", 0.1)
        self.assertEqual(30.0, result["utilization_percent"])
        self.assertEqual(
            {"1m": 1.0, "5m": 2.0, "15m": 3.0},
            result["load_average"],
        )

    def test_windows_memory_uses_native_status_values(self) -> None:
        with mock.patch.object(
            probe, "_windows_memory_status", return_value=(16_000, 4_000)
        ):
            self.assertEqual(
                {"total_bytes": 16_000, "available_bytes": 4_000},
                probe._collect_memory("Windows"),
            )

    def test_macos_memory_combines_sysctl_total_with_vm_stat_available(
        self,
    ) -> None:
        vm_stat = (FIXTURES / "macos-vm-stat.txt").read_text(encoding="utf-8")
        results = (
            probe.CommandResult(0, "17179869184\n", ""),
            probe.CommandResult(0, vm_stat, ""),
        )
        with (
            mock.patch.object(probe, "run_command", side_effect=results),
            mock.patch.object(
                probe,
                "resolve_trusted_executable",
                side_effect=(
                    Path("/usr/bin/sysctl"),
                    Path("/usr/bin/vm_stat"),
                ),
            ),
        ):
            memory = probe._collect_memory("Darwin")
        self.assertEqual(17_179_869_184, memory["total_bytes"])
        self.assertEqual((100 + 200 + 10) * 16_384, memory["available_bytes"])

    def test_cpu_sampling_failure_preserves_logical_cpus_and_load_average(
        self,
    ) -> None:
        self.assertIn(
            "unavailable",
            inspect.signature(probe._collect_cpu).parameters,
        )
        unavailable: list[dict[str, str]] = []
        with (
            mock.patch.object(probe.os, "cpu_count", return_value=8),
            mock.patch.object(
                probe.os,
                "getloadavg",
                return_value=(0.25, 0.5, 0.75),
                create=True,
            ),
            mock.patch.object(
                probe.Path,
                "read_text",
                side_effect=PermissionError("proc stat denied"),
            ),
        ):
            result = probe._collect_cpu("Linux", 0.1, unavailable)

        self.assertEqual(8, result["logical_cpus"])
        self.assertEqual(
            {"1m": 0.25, "5m": 0.5, "15m": 0.75},
            result["load_average"],
        )
        self.assertNotIn("utilization_percent", result)
        self.assertIn(
            {
                "metric": "cpu.utilization_percent",
                "reason": "proc stat denied",
            },
            unavailable,
        )

    def test_windows_load_average_has_precise_unsupported_reason(self) -> None:
        self.assertIn(
            "unavailable",
            inspect.signature(probe._collect_cpu).parameters,
        )
        unavailable: list[dict[str, str]] = []
        with (
            mock.patch.object(probe.os, "cpu_count", return_value=4),
            mock.patch.object(
                probe,
                "_windows_cpu_times",
                side_effect=((100, 50), (200, 100)),
            ),
            mock.patch.object(probe.time, "sleep"),
        ):
            result = probe._collect_cpu("Windows", 0.1, unavailable)

        self.assertEqual(50.0, result["utilization_percent"])
        self.assertNotIn("load_average", result)
        self.assertIn(
            {
                "metric": "cpu.load_average",
                "reason": "load average is unsupported on Windows",
            },
            unavailable,
        )

    def test_macos_memory_preserves_total_when_vm_stat_fails(self) -> None:
        self.assertIn(
            "unavailable",
            inspect.signature(probe._collect_memory).parameters,
        )
        unavailable: list[dict[str, str]] = []
        with mock.patch.object(
            probe,
            "_checked_stdout",
            side_effect=("17179869184\n", PermissionError("vm_stat denied")),
        ):
            result = probe._collect_memory("Darwin", unavailable)

        self.assertEqual({"total_bytes": 17_179_869_184}, result)
        self.assertIn(
            {
                "metric": "memory.available_bytes",
                "reason": "vm_stat denied",
            },
            unavailable,
        )

    def test_macos_memory_preserves_available_when_sysctl_fails(self) -> None:
        self.assertIn(
            "unavailable",
            inspect.signature(probe._collect_memory).parameters,
        )
        vm_stat = (FIXTURES / "macos-vm-stat.txt").read_text(encoding="utf-8")
        unavailable: list[dict[str, str]] = []
        with mock.patch.object(
            probe,
            "_checked_stdout",
            side_effect=(PermissionError("sysctl denied"), vm_stat),
        ):
            result = probe._collect_memory("Darwin", unavailable)

        self.assertEqual(
            {"available_bytes": (100 + 200 + 10) * 16_384},
            result,
        )
        self.assertIn(
            {
                "metric": "memory.total_bytes",
                "reason": "sysctl denied",
            },
            unavailable,
        )

    def test_gpu_base_failure_does_not_suppress_nvidia_success(self) -> None:
        base_collector = getattr(probe, "_base_gpu_devices", None)
        self.assertIsNotNone(base_collector)
        unavailable: list[dict[str, str]] = []
        nvidia_device = probe._graphics_device(
            name="NVIDIA Test",
            vendor="NVIDIA",
            memory_bytes=1024,
            driver_version="1",
            detection_source="nvidia-smi",
            backend_name="cuda-driver",
        )
        with (
            mock.patch.object(
                probe,
                "_base_gpu_devices",
                side_effect=PermissionError("base discovery denied"),
            ),
            mock.patch.object(
                probe,
                "resolve_trusted_executable",
                return_value=Path("/usr/bin/nvidia-smi"),
            ),
            mock.patch.object(
                probe, "_nvidia_devices", return_value=[nvidia_device]
            ),
        ):
            result = probe._collect_gpu("Linux", unavailable)

        self.assertEqual([nvidia_device], result["devices"])
        self.assertIn(
            {"metric": "gpu.base", "reason": "base discovery denied"},
            unavailable,
        )

    def test_gpu_nvidia_failure_does_not_suppress_base_success(self) -> None:
        base_collector = getattr(probe, "_base_gpu_devices", None)
        self.assertIsNotNone(base_collector)
        unavailable: list[dict[str, str]] = []
        base_device = probe._graphics_device(
            name="Intel Test",
            vendor="Intel",
            memory_bytes=None,
            driver_version=None,
            detection_source="linux-sysfs",
            backend_name="graphics-device",
        )
        with (
            mock.patch.object(
                probe, "_base_gpu_devices", return_value=[base_device]
            ),
            mock.patch.object(
                probe,
                "resolve_trusted_executable",
                side_effect=FileNotFoundError(
                    "no trusted executable candidate for nvidia-smi"
                ),
            ),
        ):
            result = probe._collect_gpu("Linux", unavailable)

        self.assertEqual([base_device], result["devices"])
        self.assertIn(
            {
                "metric": "gpu.nvidia",
                "reason": "no trusted executable candidate for nvidia-smi",
            },
            unavailable,
        )

    def test_successful_zero_device_sources_are_not_marked_unavailable(
        self,
    ) -> None:
        base_collector = getattr(probe, "_base_gpu_devices", None)
        self.assertIsNotNone(base_collector)
        unavailable: list[dict[str, str]] = []
        with (
            mock.patch.object(probe, "_base_gpu_devices", return_value=[]),
            mock.patch.object(
                probe,
                "resolve_trusted_executable",
                return_value=Path("/usr/bin/nvidia-smi"),
            ),
            mock.patch.object(probe, "_nvidia_devices", return_value=[]),
        ):
            result = probe._collect_gpu("Linux", unavailable)

        self.assertEqual({"devices": []}, result)
        self.assertEqual([], unavailable)

    def test_nvidia_empty_output_is_a_successful_zero_device_result(self) -> None:
        self.assertIn(
            "allow_empty",
            inspect.signature(probe._checked_stdout).parameters,
        )
        with mock.patch.object(
            probe,
            "run_command",
            return_value=probe.CommandResult(0, "", ""),
        ):
            self.assertEqual(
                [],
                probe._nvidia_devices(Path("/usr/bin/nvidia-smi")),
            )

    def test_windows_gpu_uses_cim_json_with_bounded_command_wrapper(self) -> None:
        gpu_json = (FIXTURES / "windows-gpu.json").read_text(encoding="utf-8")
        with (
            mock.patch.object(
                probe, "run_command", return_value=probe.CommandResult(0, gpu_json, "")
            ) as command,
            mock.patch.object(
                probe,
                "resolve_trusted_executable",
                side_effect=(
                    Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"),
                    FileNotFoundError(
                        "no trusted executable candidate for nvidia-smi"
                    ),
                ),
                create=True,
            ),
        ):
            result = probe._collect_gpu("Windows")
        self.assertEqual(2, len(result["devices"]))
        args = command.call_args.args[0]
        windows_executable = PureWindowsPath(os.fspath(args[0]))
        self.assertTrue(windows_executable.is_absolute())
        self.assertEqual("powershell.exe", windows_executable.name)
        self.assertIn("Win32_VideoController", args[-1])

    def test_windows_processes_use_cim_and_privacy_preserving_parser(self) -> None:
        process_json = (FIXTURES / "processes-windows.json").read_text(
            encoding="utf-8"
        )
        with mock.patch.object(
            probe, "run_command", return_value=probe.CommandResult(0, process_json, "")
        ) as command, mock.patch.object(
            probe,
            "resolve_trusted_executable",
            return_value=Path(
                "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
            ),
            create=True,
        ):
            processes = probe._collect_processes("Windows")
        self.assertEqual(2, len(processes))
        self.assertEqual(ProcessParserTests.ALLOWED_KEYS, set(processes[0]))
        self.assertIn(
            "Win32_PerfFormattedData_PerfProc_Process",
            command.call_args.args[0][-1],
        )


class SampleValidationTests(unittest.TestCase):
    def test_accepts_inclusive_sampling_boundaries(self) -> None:
        self.assertEqual(0.1, probe.validate_sample_seconds("0.1"))
        self.assertEqual(10.0, probe.validate_sample_seconds("10"))

    def test_rejects_out_of_range_non_finite_and_non_numeric_sampling(self) -> None:
        for value in ("0", "10.1", "nan", "inf", "-inf", "not-a-number"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    probe.validate_sample_seconds(value)


class CommandTests(unittest.TestCase):
    class FakeProcess:
        def __init__(
            self,
            stdout: bytes = b"",
            stderr: bytes = b"",
            running: bool = False,
        ) -> None:
            self.stdout: object | None = None
            self.stderr: object | None = None
            self.returncode = None if running else 0
            self.killed = False
            self.waited = False
            self.attach_output(stdout, stderr)

        def attach_output(
            self,
            stdout: bytes = b"",
            stderr: bytes = b"",
        ) -> None:
            for channel, data in (
                ("stdout", stdout),
                ("stderr", stderr),
            ):
                existing = getattr(self, channel)
                if existing is not None:
                    existing.close()
                read_descriptor, write_descriptor = os.pipe()
                try:
                    if data:
                        os.write(write_descriptor, data)
                finally:
                    os.close(write_descriptor)
                setattr(
                    self,
                    channel,
                    os.fdopen(read_descriptor, "rb", buffering=0),
                )

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: float | None = None) -> int:
            self.waited = True
            if self.returncode is None:
                self.returncode = -9
            return self.returncode

        def kill(self) -> None:
            self.killed = True
            self.returncode = -9

    @contextlib.contextmanager
    def trusted_test_runtime(self) -> object:
        """Isolate command-I/O tests from host trust-root policy."""
        with (
            mock.patch.object(
                probe,
                "_trusted_working_directory",
                return_value=Path.cwd().resolve(),
            ),
            mock.patch.object(
                probe,
                "_sanitized_environment",
                return_value=dict(os.environ),
            ),
        ):
            yield

    def test_run_command_rejects_invalid_timeout_before_starting_process(
        self,
    ) -> None:
        invalid_timeouts = (0, -1, 5.1, float("nan"), float("inf"), "invalid")
        for timeout in invalid_timeouts:
            with self.subTest(timeout=timeout), mock.patch.object(
                probe.subprocess, "Popen"
            ) as popen:
                with self.assertRaises(ValueError):
                    probe.run_command([sys.executable, "-V"], timeout_seconds=timeout)
                popen.assert_not_called()

    def test_run_command_accepts_five_second_binding_maximum(self) -> None:
        with self.trusted_test_runtime():
            result = probe.run_command(
                [sys.executable, "-V"],
                timeout_seconds=5.0,
            )
        self.assertEqual(0, result.returncode)
        self.assertIn("Python", result.stdout)

    def test_run_command_rejects_non_absolute_executable_before_start(
        self,
    ) -> None:
        with mock.patch.object(probe.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(
                ValueError, "absolute executable path"
            ):
                probe.run_command(["python", "-V"])
        popen.assert_not_called()

    def test_start_failure_does_not_expose_executable_path(self) -> None:
        error_type = getattr(probe, "CommandStartError", None)
        self.assertIsNotNone(error_type)
        secret_path = str(Path(tempfile.gettempdir()) / "sensitive-tool.exe")
        with self.trusted_test_runtime(), mock.patch.object(
            probe.subprocess,
            "Popen",
            side_effect=FileNotFoundError(2, "missing", secret_path),
        ):
            with self.assertRaises(error_type) as caught:
                probe.run_command([sys.executable, "-V"])
        self.assertNotIn(secret_path, str(caught.exception))
        self.assertEqual(
            "diagnostic child could not be started",
            str(caught.exception),
        )

    def test_start_permission_failure_preserves_bounded_reason(self) -> None:
        secret_path = str(Path(tempfile.gettempdir()) / "sensitive-tool.exe")
        with self.trusted_test_runtime(), mock.patch.object(
            probe.subprocess,
            "Popen",
            side_effect=PermissionError(13, "denied", secret_path),
        ):
            with self.assertRaises(probe.CommandStartError) as caught:
                probe.run_command([sys.executable, "-V"])
        self.assertNotIn(secret_path, str(caught.exception))
        self.assertEqual(
            "diagnostic child permission denied",
            str(caught.exception),
        )

    def test_run_command_captures_utf8_output_without_a_shell(self) -> None:
        with self.trusted_test_runtime():
            result = probe.run_command(
                [
                    sys.executable,
                    "-c",
                    "import sys; "
                    "sys.stdout.buffer.write("
                    "'resource probe \\u2713'.encode('utf-8'))",
                ],
                timeout_seconds=2.0,
            )
        self.assertEqual(0, result.returncode)
        self.assertEqual("resource probe ✓", result.stdout.strip())
        self.assertEqual("", result.stderr)

    def test_command_mechanics_use_runtime_kernel_not_collector_platform(
        self,
    ) -> None:
        mocked_collector_systems = (
            ("Linux", "Darwin")
            if os.name == "nt"
            else ("Windows",)
        )
        for mocked_collector_system in mocked_collector_systems:
            child = self.FakeProcess(stdout=b"ok")
            with (
                self.subTest(
                    mocked_collector_system=mocked_collector_system,
                ),
                mock.patch.object(
                    probe.platform,
                    "system",
                    return_value=mocked_collector_system,
                ),
                mock.patch.object(
                    probe.subprocess,
                    "Popen",
                    return_value=child,
                ) as popen,
                mock.patch.object(
                    probe,
                    "_trusted_working_directory",
                    return_value=Path(os.path.abspath(os.sep)),
                ),
                mock.patch.object(
                    probe,
                    "_sanitized_environment",
                    return_value={},
                ),
            ):
                result = probe.run_command([sys.executable, "-V"])

            self.assertEqual("ok", result.stdout)
            options = popen.call_args.kwargs
            if os.name == "nt":
                self.assertIn("creationflags", options)
                self.assertNotIn("start_new_session", options)
            else:
                self.assertTrue(options["start_new_session"])
                self.assertNotIn("creationflags", options)

    def test_run_command_uses_trusted_cwd_and_sanitized_environment(self) -> None:
        child = self.FakeProcess()
        sinks: list[object] = []

        def start_child(*args: object, **kwargs: object) -> object:
            child.attach_output(stdout=b"ok")
            sinks.extend((child.stdout, child.stderr))
            return child

        trusted_cwd = Path(os.path.abspath(os.sep))
        expected_environment = {"LANG": "C", "LC_ALL": "C"}
        with (
            self.trusted_test_runtime(),
            mock.patch.object(
                probe.subprocess,
                "Popen",
                side_effect=start_child,
            ) as popen,
            mock.patch.object(
                probe.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    [sys.executable, "-V"],
                    0,
                    "ok",
                    "",
                ),
            ),
            mock.patch.dict(
                probe.os.environ,
                {
                    "PATH": "project-shadow",
                    "PYTHONPATH": "project-python",
                    "VIRTUAL_ENV": "project-venv",
                    "HOME": "project-home",
                    "SystemRoot": "C:\\Windows",
                },
                clear=True,
            ),
            mock.patch.object(
                probe,
                "_trusted_working_directory",
                return_value=trusted_cwd,
            ),
            mock.patch.object(
                probe,
                "_sanitized_environment",
                return_value=expected_environment,
            ),
        ):
            result = probe.run_command([sys.executable, "-V"])

        self.assertEqual("ok", result.stdout)
        self.assertTrue(popen.called)
        kwargs = popen.call_args.kwargs
        self.assertFalse(kwargs["shell"])
        self.assertEqual(os.fspath(trusted_cwd), kwargs["cwd"])
        self.assertEqual(expected_environment, kwargs["env"])
        self.assertNotIn("PATH", kwargs["env"])
        self.assertNotIn("PYTHONPATH", kwargs["env"])
        self.assertNotIn("VIRTUAL_ENV", kwargs["env"])
        self.assertNotIn("HOME", kwargs["env"])
        self.assertTrue(all(sink.closed for sink in sinks))

    def test_windows_environment_uses_native_validated_roots_not_spoofed_env(
        self,
    ) -> None:
        native_windows = Path("/native/windows")
        native_system = native_windows / "System32"
        native_program_files = Path("/native/program-files")
        system_modules = (
            native_system
            / "WindowsPowerShell"
            / "v1.0"
            / "Modules"
        )
        program_files_modules = (
            native_program_files
            / "WindowsPowerShell"
            / "Modules"
        )
        with (
            mock.patch.object(probe.platform, "system", return_value="Windows"),
            mock.patch.object(
                probe,
                "_windows_directory",
                return_value=native_windows,
                create=True,
            ),
            mock.patch.object(
                probe,
                "_windows_system_directory",
                return_value=native_system,
                create=True,
            ),
            mock.patch.object(
                probe,
                "_windows_program_files_directory",
                return_value=native_program_files,
                create=True,
            ),
            mock.patch.object(
                probe,
                "_windows_path_is_secure",
                return_value=True,
                create=True,
            ),
            mock.patch.dict(
                probe.os.environ,
                {
                    "SystemRoot": "/spoof/windows",
                    "WINDIR": "/spoof/windows",
                    "ProgramFiles": "/spoof/program-files",
                    "PATH": "/spoof/path",
                    "CUDA_PATH": "/spoof/cuda",
                    "PSModulePath": "/spoof/modules",
                },
                clear=True,
            ),
        ):
            environment = probe._sanitized_environment()

        self.assertEqual(
            {
                "SystemRoot": str(native_windows),
                "WINDIR": str(native_windows),
                "ProgramFiles": str(native_program_files),
                "PSModulePath": (
                    f"{system_modules};{program_files_modules}"
                ),
            },
            environment,
        )
        self.assertNotIn("/spoof/modules", environment["PSModulePath"])

    def test_windows_environment_rejects_untrusted_all_users_modules(
        self,
    ) -> None:
        native_windows = Path("/native/windows")
        native_system = native_windows / "System32"
        native_program_files = Path("/native/program-files")
        program_files_modules = (
            native_program_files
            / "WindowsPowerShell"
            / "Modules"
        )

        def secure_path(
            candidate: Path,
            *args: object,
            **kwargs: object,
        ) -> bool:
            return candidate != program_files_modules

        with (
            mock.patch.object(probe.platform, "system", return_value="Windows"),
            mock.patch.object(
                probe,
                "_windows_directory",
                return_value=native_windows,
            ),
            mock.patch.object(
                probe,
                "_windows_system_directory",
                return_value=native_system,
            ),
            mock.patch.object(
                probe,
                "_windows_program_files_directory",
                return_value=native_program_files,
            ),
            mock.patch.object(
                probe,
                "_windows_path_is_secure",
                side_effect=secure_path,
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "PowerShell modules",
            ):
                probe._sanitized_environment()

    @unittest.skipUnless(
        os.name == "nt",
        "requires Windows PowerShell module auto-loading",
    )
    def test_windows_user_module_shadow_is_not_auto_loaded(self) -> None:
        try:
            powershell = probe.resolve_trusted_executable(
                "powershell.exe",
                system="Windows",
            )
            probe._sanitized_environment()
        except (FileNotFoundError, OSError) as exc:
            self.skipTest(
                "native Windows trust roots fail closed on this host: "
                f"{type(exc).__name__}"
            )
        documents_result = subprocess.run(
            [
                os.fspath(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "[Environment]::GetFolderPath('MyDocuments')",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        documents = Path(documents_result.stdout.strip())
        if documents_result.returncode != 0 or not documents.is_absolute():
            self.skipTest("current-user Documents directory is unavailable")

        module_root = (
            documents
            / "WindowsPowerShell"
            / "Modules"
        )
        fixture = module_root / "ResourceProbeShadowFixture"
        if fixture.exists():
            self.skipTest("shadow fixture path already exists")

        created_parents: list[Path] = []
        current = module_root
        while not current.exists() and current != documents:
            created_parents.append(current)
            current = current.parent

        try:
            fixture.mkdir(parents=True)
            (fixture / "ResourceProbeShadowFixture.psd1").write_text(
                "@{\n"
                "RootModule='ResourceProbeShadowFixture.psm1'\n"
                "ModuleVersion='1.0.0'\n"
                "GUID='cb7ab8f9-df51-412a-8adb-d13f82f275a5'\n"
                "FunctionsToExport=@('Get-ResourceProbeShadowFixture')\n"
                "CmdletsToExport=@()\n"
                "AliasesToExport=@()\n"
                "}\n",
                encoding="utf-8",
            )
            (fixture / "ResourceProbeShadowFixture.psm1").write_text(
                "function Get-ResourceProbeShadowFixture {\n"
                "    'USER-MODULE-SHADOWED'\n"
                "}\n",
                encoding="utf-8",
            )

            result = probe.run_command(
                [
                    os.fspath(powershell),
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$ErrorActionPreference = 'SilentlyContinue'; "
                    "Import-Module ResourceProbeShadowFixture; "
                    "if ($null -eq "
                    "(Get-Module ResourceProbeShadowFixture)) { "
                    "'SYSTEM-MODULES-ONLY' "
                    "} else { Get-ResourceProbeShadowFixture }",
                ],
                timeout_seconds=5.0,
            )
        finally:
            shutil.rmtree(fixture, ignore_errors=True)
            for created in created_parents:
                try:
                    created.rmdir()
                except OSError:
                    pass

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("SYSTEM-MODULES-ONLY", result.stdout.strip())

    def test_output_overflow_kills_only_owned_child_and_caps_capture(
        self,
    ) -> None:
        output_limit = getattr(probe, "MAX_COMMAND_OUTPUT_BYTES", None)
        error_type = getattr(probe, "CommandOutputLimitError", None)
        self.assertEqual(1_048_576, output_limit)
        self.assertIsNotNone(error_type)
        child = self.FakeProcess(running=True)
        sinks: list[object] = []

        def start_child(*args: object, **kwargs: object) -> object:
            child.attach_output(
                stdout=b"x" * 7,
                stderr=b"y" * 4,
            )
            sinks.extend((child.stdout, child.stderr))
            return child

        with (
            self.trusted_test_runtime(),
            mock.patch.object(
                probe.subprocess,
                "Popen",
                side_effect=start_child,
            ),
            mock.patch.object(
                probe,
                "MAX_COMMAND_OUTPUT_BYTES",
                8,
            ),
        ):
            with self.assertRaises(error_type) as caught:
                probe.run_command([sys.executable, "-V"])

        self.assertLessEqual(
            caught.exception.captured_bytes,
            8,
        )
        self.assertTrue(child.killed)
        self.assertTrue(child.waited)
        self.assertTrue(all(sink.closed for sink in sinks))

    def test_bounded_output_never_retains_more_than_combined_limit(
        self,
    ) -> None:
        capture_type = getattr(probe, "_BoundedOutput", None)
        self.assertIsNotNone(capture_type)
        capture = capture_type(8)

        capture.append("stdout", b"123456")
        capture.append("stderr", b"abcdef")

        self.assertEqual(8, capture.retained_bytes)
        self.assertEqual(b"123456", capture.stdout_bytes)
        self.assertEqual(b"ab", capture.stderr_bytes)
        self.assertTrue(capture.overflowed)

    def test_high_throughput_dual_stream_output_uses_bounded_pipes(
        self,
    ) -> None:
        output_limit = 65_536
        child_code = (
            "import os;"
            "chunk=b'x'*8192;"
            "[(os.write(1,chunk),os.write(2,chunk)) "
            "for _ in range(4096)]"
        )
        started = time.monotonic()
        with (
            self.trusted_test_runtime(),
            mock.patch.object(
                probe,
                "MAX_COMMAND_OUTPUT_BYTES",
                output_limit,
            ),
            mock.patch.object(
                tempfile,
                "TemporaryFile",
                side_effect=AssertionError(
                    "disk-backed capture is forbidden"
                ),
            ),
        ):
            with self.assertRaises(
                probe.CommandOutputLimitError
            ) as caught:
                probe.run_command(
                    [sys.executable, "-c", child_code],
                    timeout_seconds=2.0,
                )
        elapsed = time.monotonic() - started

        self.assertEqual(output_limit, caught.exception.captured_bytes)
        self.assertLess(
            elapsed,
            2.0 + probe.COMMAND_CLEANUP_GRACE_SECONDS + 0.5,
            f"output handling exceeded its deadline: {elapsed:.3f}s",
        )

    def test_real_oversized_child_is_stopped_at_combined_byte_limit(self) -> None:
        with self.trusted_test_runtime():
            with self.assertRaises(probe.CommandOutputLimitError) as caught:
                probe.run_command(
                    [
                        sys.executable,
                        "-c",
                        "import sys,time;"
                        "sys.stdout.buffer.write(b'x'*1048577);"
                        "sys.stdout.buffer.flush();"
                        "time.sleep(2)",
                    ],
                    timeout_seconds=2.0,
                )
        self.assertEqual(
            probe.MAX_COMMAND_OUTPUT_BYTES,
            caught.exception.captured_bytes,
        )

    def test_timeout_kills_owned_child_waits_and_closes_streams(self) -> None:
        error_type = getattr(probe, "CommandTimeoutError", None)
        self.assertIsNotNone(error_type)
        child = self.FakeProcess(running=True)
        sinks: list[object] = []

        def start_child(*args: object, **kwargs: object) -> object:
            sinks.extend((child.stdout, child.stderr))
            return child

        with self.trusted_test_runtime(), mock.patch.object(
            probe.subprocess,
            "Popen",
            side_effect=start_child,
        ):
            with self.assertRaisesRegex(
                error_type,
                "diagnostic child timed out",
            ):
                probe.run_command(
                    [sys.executable, "-V"],
                    timeout_seconds=0.05,
                )

        self.assertTrue(child.killed)
        self.assertTrue(child.waited)
        self.assertTrue(all(sink.closed for sink in sinks))

    def test_cleanup_wait_cannot_exceed_fixed_grace(self) -> None:
        class NeverReapedProcess(self.FakeProcess):
            def kill(self) -> None:
                self.killed = True

            def wait(self, timeout: float | None = None) -> int:
                self.waited = True
                if timeout:
                    time.sleep(timeout)
                raise subprocess.TimeoutExpired(["diagnostic"], timeout)

        child = NeverReapedProcess(running=True)
        started = time.monotonic()
        with (
            mock.patch.object(
                probe.platform,
                "system",
                return_value="Windows",
            ),
            mock.patch.object(
                probe.subprocess,
                "Popen",
                return_value=child,
            ),
            mock.patch.object(
                probe,
                "_trusted_working_directory",
                return_value=Path(os.path.abspath(os.sep)),
            ),
            mock.patch.object(
                probe,
                "_sanitized_environment",
                return_value={},
            ),
        ):
            with self.assertRaises(probe.CommandTimeoutError):
                probe.run_command(
                    [sys.executable, "-V"],
                    timeout_seconds=0.05,
                )
        elapsed = time.monotonic() - started

        self.assertTrue(child.killed)
        self.assertTrue(child.waited)
        self.assertLess(
            elapsed,
            0.5,
            f"cleanup exceeded timeout plus fixed grace: {elapsed:.3f}s",
        )

    def test_real_timed_out_child_is_stopped_before_natural_exit(self) -> None:
        started = time.monotonic()
        with self.trusted_test_runtime():
            with self.assertRaises(probe.CommandTimeoutError):
                probe.run_command(
                    [sys.executable, "-c", "import time; time.sleep(2)"],
                    timeout_seconds=0.05,
                )
        self.assertLess(time.monotonic() - started, 1.0)

    def test_descendant_inheriting_standard_handles_cannot_extend_deadline(
        self,
    ) -> None:
        child_code = (
            "import os,subprocess,sys;"
            "sys.stdout.write('parent complete\\n');"
            "sys.stdout.flush();"
            "subprocess.Popen([sys.executable,'-c',"
            "'import time; time.sleep(4)']);"
            "os._exit(0)"
        )
        started = time.monotonic()
        with self.trusted_test_runtime():
            result = probe.run_command(
                [sys.executable, "-c", child_code],
                timeout_seconds=2.0,
            )
        elapsed = time.monotonic() - started

        self.assertEqual(0, result.returncode)
        self.assertIn("parent complete", result.stdout)
        self.assertLess(
            elapsed,
            3.0,
            f"descendant-held standard handles extended call to {elapsed:.3f}s",
        )

    def test_trusted_resolution_uses_native_windows_anchor_not_environment(
        self,
    ) -> None:
        resolver = getattr(probe, "resolve_trusted_executable", None)
        self.assertIsNotNone(resolver)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            system_root = root / "Windows"
            trusted = (
                system_root
                / "System32"
                / "WindowsPowerShell"
                / "v1.0"
                / "powershell.exe"
            )
            trusted.parent.mkdir(parents=True)
            trusted.write_bytes(b"trusted")
            shadow = root / "project"
            shadow.mkdir()
            (shadow / "powershell.exe").write_bytes(b"shadow")

            with (
                mock.patch.object(
                    probe,
                    "_windows_directory",
                    return_value=system_root,
                    create=True,
                ),
                mock.patch.object(
                    probe,
                    "_windows_system_directory",
                    return_value=system_root / "System32",
                    create=True,
                ),
                mock.patch.object(
                    probe,
                    "_windows_program_files_directory",
                    return_value=root / "Program Files",
                    create=True,
                ),
                mock.patch.object(
                    probe,
                    "_windows_path_is_secure",
                    side_effect=lambda candidate, *args, **kwargs: candidate.is_file(),
                    create=True,
                ),
                mock.patch.dict(
                    probe.os.environ,
                    {
                        "SystemRoot": str(shadow),
                        "WINDIR": str(shadow),
                        "PATH": str(shadow),
                    },
                    clear=True,
                ),
                mock.patch.object(probe.os, "getcwd", return_value=str(shadow)),
            ):
                resolved = resolver(
                    "powershell.exe",
                    system="Windows",
                )
                self.assertTrue(trusted.samefile(resolved))
                self.assertFalse((shadow / "powershell.exe").samefile(resolved))

    def test_windows_nvidia_resolution_uses_native_program_files_anchor(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program_files = root / "Program Files"
            trusted = (
                program_files
                / "NVIDIA Corporation"
                / "NVSMI"
                / "nvidia-smi.exe"
            )
            trusted.parent.mkdir(parents=True)
            trusted.write_bytes(b"trusted")
            shadow = root / "project"
            shadow.mkdir()
            (shadow / "nvidia-smi.exe").write_bytes(b"shadow")

            with (
                mock.patch.object(
                    probe,
                    "_windows_directory",
                    return_value=root / "Windows",
                    create=True,
                ),
                mock.patch.object(
                    probe,
                    "_windows_system_directory",
                    return_value=root / "Windows" / "System32",
                    create=True,
                ),
                mock.patch.object(
                    probe,
                    "_windows_program_files_directory",
                    return_value=program_files,
                    create=True,
                ),
                mock.patch.object(
                    probe,
                    "_windows_path_is_secure",
                    side_effect=lambda candidate, *args, **kwargs: candidate.is_file(),
                    create=True,
                ),
                mock.patch.dict(
                    probe.os.environ,
                    {
                        "ProgramFiles": str(shadow),
                        "PATH": str(shadow),
                    },
                    clear=True,
                ),
            ):
                resolved = probe.resolve_trusted_executable(
                    "nvidia-smi",
                    system="Windows",
                )
                self.assertTrue(trusted.samefile(resolved))
                self.assertFalse((shadow / "nvidia-smi.exe").samefile(resolved))

    @unittest.skipUnless(
        os.name == "nt",
        "requires Windows token access checks",
    )
    def test_windows_path_security_rejects_user_writable_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trusted_root = Path(temporary)
            candidate = trusted_root / "tool.exe"
            candidate.write_bytes(b"test")
            self.assertFalse(
                probe._windows_path_is_secure(candidate, trusted_root)
            )

    def test_windows_access_check_accepts_only_definitive_denials(self) -> None:
        invalid_handle = probe.ctypes.c_void_p(-1).value
        for error_code in (5, 1314):
            create_file = mock.Mock(return_value=invalid_handle)
            close_handle = mock.Mock(return_value=1)
            kernel32 = SimpleNamespace(
                CreateFileW=create_file,
                CloseHandle=close_handle,
            )
            with (
                self.subTest(error_code=error_code),
                mock.patch.object(
                    probe.platform,
                    "system",
                    return_value="Windows",
                ),
                mock.patch.object(
                    probe.ctypes,
                    "WinDLL",
                    return_value=kernel32,
                    create=True,
                ),
                mock.patch.object(
                    probe.ctypes,
                    "set_last_error",
                    create=True,
                ),
                mock.patch.object(
                    probe.ctypes,
                    "get_last_error",
                    return_value=error_code,
                    create=True,
                ),
            ):
                self.assertFalse(
                    probe._windows_current_user_can_write(
                        Path("C:/Windows"),
                        directory=True,
                    )
                )
            self.assertEqual(6, create_file.call_count)
            close_handle.assert_not_called()

    def test_windows_access_check_rejects_indeterminate_api_errors(self) -> None:
        invalid_handle = probe.ctypes.c_void_p(-1).value
        for error_code in (0, 2, 32, 33):
            create_file = mock.Mock(return_value=invalid_handle)
            kernel32 = SimpleNamespace(
                CreateFileW=create_file,
                CloseHandle=mock.Mock(return_value=1),
            )
            with (
                self.subTest(error_code=error_code),
                mock.patch.object(
                    probe.platform,
                    "system",
                    return_value="Windows",
                ),
                mock.patch.object(
                    probe.ctypes,
                    "WinDLL",
                    return_value=kernel32,
                    create=True,
                ),
                mock.patch.object(
                    probe.ctypes,
                    "set_last_error",
                    create=True,
                ),
                mock.patch.object(
                    probe.ctypes,
                    "get_last_error",
                    return_value=error_code,
                    create=True,
                ),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "indeterminate",
                ):
                    probe._windows_current_user_can_write(
                        Path("C:/Windows"),
                        directory=True,
                    )

    @unittest.skipUnless(
        os.name == "nt",
        "requires live Windows trust-root checks",
    )
    def test_windows_native_system_directory_is_secure_live(self) -> None:
        windows_directory = probe._windows_directory()
        system_directory = probe._windows_system_directory()
        secure = probe._windows_path_is_secure(
            system_directory,
            windows_directory,
            expect_file=False,
        )
        if not secure:
            self.skipTest(
                "native Windows trust root is writable or indeterminate; "
                "the probe correctly fails closed"
            )
        self.assertTrue(secure)

    @unittest.skipUnless(
        os.name == "nt",
        "requires Windows junction semantics",
    )
    def test_windows_path_security_rejects_reparse_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            candidate = target / "tool.exe"
            candidate.write_bytes(b"test")
            junction = root / "junction"
            result = subprocess.run(
                [
                    os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe"),
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(junction),
                    str(target),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest(
                    "Windows junction creation unavailable: "
                    + (result.stderr.strip() or result.stdout.strip())
                )
            with mock.patch.object(
                probe,
                "_windows_current_user_can_write",
                return_value=False,
            ):
                self.assertFalse(
                    probe._windows_path_is_secure(
                        junction / candidate.name,
                        junction,
                    )
                )

    def test_posix_resolution_ignores_path_shadow_and_rejects_symlink(
        self,
    ) -> None:
        resolver = getattr(probe, "resolve_trusted_executable", None)
        self.assertIsNotNone(resolver)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trusted_root = root / "usr" / "bin"
            trusted_root.mkdir(parents=True)
            trusted = trusted_root / "ps"
            trusted.write_bytes(b"trusted")
            trusted.chmod(0o555)
            shadow = root / "project"
            shadow.mkdir()
            (shadow / "ps").write_bytes(b"shadow")

            with (
                mock.patch.object(
                    probe,
                    "POSIX_TRUSTED_DIRECTORIES",
                    (trusted_root,),
                ),
                mock.patch.object(
                    probe,
                    "_posix_candidate_is_secure",
                    return_value=True,
                    create=True,
                ),
                mock.patch.dict(probe.os.environ, {"PATH": str(shadow)}, clear=True),
            ):
                self.assertTrue(
                    trusted.samefile(resolver("ps", system="Linux"))
                )
                original_is_symlink = Path.is_symlink

                def simulated_symlink(path: Path) -> bool:
                    return path == trusted or original_is_symlink(path)

                with mock.patch.object(
                    probe.Path,
                    "is_symlink",
                    autospec=True,
                    side_effect=simulated_symlink,
                ):
                    with self.assertRaisesRegex(
                        FileNotFoundError,
                        "no trusted executable candidate for ps",
                    ):
                        resolver("ps", system="Linux")

    def test_posix_metadata_rejects_user_owned_0555_executable(self) -> None:
        metadata = SimpleNamespace(
            st_uid=1000,
            st_mode=stat.S_IFREG | 0o555,
        )
        self.assertFalse(
            probe._posix_metadata_is_secure(
                metadata,
                require_directory=False,
            )
        )

    def test_posix_metadata_rejects_writable_parent_directory(self) -> None:
        metadata = SimpleNamespace(
            st_uid=0,
            st_mode=stat.S_IFDIR | 0o775,
        )
        self.assertFalse(
            probe._posix_metadata_is_secure(
                metadata,
                require_directory=True,
            )
        )

    def test_posix_candidate_rejects_acl_granted_current_user_write(self) -> None:
        candidate = Path("/usr/bin/ps")
        root = Path("/usr/bin")
        trusted_metadata = SimpleNamespace(
            st_uid=0,
            st_mode=stat.S_IFREG | 0o555,
        )
        trusted_directory = SimpleNamespace(
            st_uid=0,
            st_mode=stat.S_IFDIR | 0o755,
        )

        def metadata(path: Path) -> object:
            return trusted_metadata if path == candidate else trusted_directory

        with (
            mock.patch.object(probe.Path, "stat", autospec=True, side_effect=metadata),
            mock.patch.object(probe.Path, "is_symlink", return_value=False),
            mock.patch.object(
                probe,
                "_posix_current_user_can_write",
                return_value=True,
                create=True,
            ),
        ):
            self.assertFalse(
                probe._posix_candidate_is_secure(candidate, root)
            )

    @unittest.skipUnless(
        os.name == "posix" and shutil.which("setfacl"),
        "requires POSIX plus setfacl to exercise a real ACL",
    )
    def test_posix_acl_write_capability_is_detected_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "tool"
            candidate.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            candidate.chmod(0o555)
            subprocess.run(
                [
                    shutil.which("setfacl") or "setfacl",
                    "-m",
                    f"u:{os.getuid()}:rw",
                    str(candidate),
                ],
                check=True,
                capture_output=True,
            )
            self.assertTrue(probe._posix_current_user_can_write(candidate))


class RecommendationTests(unittest.TestCase):
    def test_recommendations_reserve_cpu_headroom(self) -> None:
        result = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 20.0},
            {"total_bytes": 100, "available_bytes": 60},
        )
        self.assertEqual("balanced", result["selected_profile"])
        self.assertEqual(6, result["profiles"]["low-impact"]["max_workers"])
        self.assertEqual(7, result["profiles"]["balanced"]["max_workers"])
        self.assertEqual(7, result["profiles"]["throughput"]["max_workers"])
        self.assertTrue(result["reasons"])

    def test_low_memory_or_critical_cpu_caps_every_profile_to_one(self) -> None:
        for cpu_percent, available in ((20.0, 24), (90.0, 80)):
            with self.subTest(cpu_percent=cpu_percent, available=available):
                result = probe.build_recommendation(
                    {"logical_cpus": 8, "utilization_percent": cpu_percent},
                    {"total_bytes": 100, "available_bytes": available},
                )
                workers = {
                    profile["max_workers"] for profile in result["profiles"].values()
                }
                self.assertEqual({1}, workers)
                self.assertEqual("low-impact", result["selected_profile"])

    def test_high_cpu_caps_balanced_to_half_logical_cpus(self) -> None:
        result = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 75.0},
            {"total_bytes": 100, "available_bytes": 80},
        )
        self.assertEqual(4, result["profiles"]["balanced"]["max_workers"])
        self.assertEqual("low-impact", result["selected_profile"])

    def test_one_cpu_allows_zero_workers_to_preserve_reserves(self) -> None:
        result = probe.build_recommendation(
            {"logical_cpus": 1, "utilization_percent": 20.0},
            {"total_bytes": 100, "available_bytes": 80},
        )
        self.assertEqual(
            {
                "low-impact": 0,
                "balanced": 0,
                "throughput": 0,
            },
            {
                name: profile["max_workers"]
                for name, profile in result["profiles"].items()
            },
        )

    def test_two_cpus_preserve_each_profiles_stated_reserve(self) -> None:
        result = probe.build_recommendation(
            {"logical_cpus": 2, "utilization_percent": 20.0},
            {"total_bytes": 100, "available_bytes": 80},
        )
        self.assertEqual(0, result["profiles"]["low-impact"]["max_workers"])
        self.assertEqual(1, result["profiles"]["balanced"]["max_workers"])
        self.assertEqual(1, result["profiles"]["throughput"]["max_workers"])

    def test_unknown_memory_caps_all_profiles_and_selects_low_impact(self) -> None:
        result = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 20.0},
            {"total_bytes": 100},
        )
        self.assertEqual(
            {1},
            {profile["max_workers"] for profile in result["profiles"].values()},
        )
        self.assertEqual("low-impact", result["selected_profile"])

    def test_unknown_utilization_caps_all_profiles_and_selects_low_impact(
        self,
    ) -> None:
        result = probe.build_recommendation(
            {"logical_cpus": 8},
            {"total_bytes": 100, "available_bytes": 80},
        )
        self.assertEqual(
            {1},
            {profile["max_workers"] for profile in result["profiles"].values()},
        )
        self.assertEqual("low-impact", result["selected_profile"])

    def test_memory_cap_applies_below_but_not_at_25_percent(self) -> None:
        below = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 20.0},
            {"total_bytes": 10_000, "available_bytes": 2_499},
        )
        boundary = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 20.0},
            {"total_bytes": 10_000, "available_bytes": 2_500},
        )
        self.assertEqual(
            {1}, {item["max_workers"] for item in below["profiles"].values()}
        )
        self.assertEqual(7, boundary["profiles"]["balanced"]["max_workers"])

    def test_balanced_cap_applies_at_75_but_not_just_below(self) -> None:
        below = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 74.9},
            {"total_bytes": 100, "available_bytes": 80},
        )
        boundary = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 75.0},
            {"total_bytes": 100, "available_bytes": 80},
        )
        self.assertEqual(7, below["profiles"]["balanced"]["max_workers"])
        self.assertEqual(4, boundary["profiles"]["balanced"]["max_workers"])

    def test_all_profile_cap_applies_at_90_but_not_just_below(self) -> None:
        below = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 89.9},
            {"total_bytes": 100, "available_bytes": 80},
        )
        boundary = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 90.0},
            {"total_bytes": 100, "available_bytes": 80},
        )
        self.assertEqual(6, below["profiles"]["low-impact"]["max_workers"])
        self.assertEqual(4, below["profiles"]["balanced"]["max_workers"])
        self.assertEqual(7, below["profiles"]["throughput"]["max_workers"])
        self.assertEqual(
            {1}, {item["max_workers"] for item in boundary["profiles"].values()}
        )
        self.assertEqual("low-impact", below["selected_profile"])
        self.assertEqual("low-impact", boundary["selected_profile"])


class SnapshotTests(unittest.TestCase):
    def test_collect_snapshot_rejects_invalid_programmatic_sample_seconds(
        self,
    ) -> None:
        for value in (0, 10.1, float("nan"), float("inf"), "not-a-number", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    probe.collect_snapshot(sample_seconds=value)

    def test_malformed_platform_gpu_payload_marks_gpu_base_unavailable(
        self,
    ) -> None:
        cases = (
            ("Darwin", "{}"),
            ("Windows", "[{}]"),
        )
        for system, payload in cases:
            with (
                self.subTest(system=system),
                mock.patch.object(probe.platform, "system", return_value=system),
                mock.patch.object(
                    probe,
                    "_collect_cpu",
                    return_value={
                        "logical_cpus": 8,
                        "utilization_percent": 20.0,
                    },
                ),
                mock.patch.object(
                    probe,
                    "_collect_memory",
                    return_value={"total_bytes": 100, "available_bytes": 50},
                ),
                mock.patch.object(
                    probe,
                    "_collect_disk",
                    return_value={
                        "total_bytes": 1000,
                        "used_bytes": 500,
                        "free_bytes": 500,
                    },
                ),
                mock.patch.object(probe, "_collect_power", return_value={}),
                mock.patch.object(probe, "_checked_stdout", return_value=payload),
                mock.patch.object(
                    probe,
                    "resolve_trusted_executable",
                    side_effect=FileNotFoundError(
                        "no trusted executable candidate for nvidia-smi"
                    ),
                ),
            ):
                snapshot = probe.collect_snapshot(sample_seconds=0.1)

            base_failures = [
                item
                for item in snapshot["unavailable"]
                if item["metric"] == "gpu.base"
            ]
            self.assertEqual({"devices": []}, snapshot["gpu"])
            self.assertEqual(1, len(base_failures))
            self.assertLessEqual(len(base_failures[0]["reason"]), 200)

    def test_collect_snapshot_has_exact_stable_top_level_schema(self) -> None:
        with (
            mock.patch.object(
                probe,
                "_collect_cpu",
                return_value={"logical_cpus": 8, "utilization_percent": 20.0},
            ),
            mock.patch.object(
                probe,
                "_collect_memory",
                return_value={"total_bytes": 100, "available_bytes": 50},
            ),
            mock.patch.object(
                probe,
                "_collect_disk",
                return_value={"total_bytes": 1000, "free_bytes": 500},
            ),
            mock.patch.object(probe, "_collect_gpu", return_value={"devices": []}),
            mock.patch.object(probe.platform, "system", return_value="Linux"),
        ):
            snapshot = probe.collect_snapshot(sample_seconds=0.1)

        self.assertEqual(REQUIRED_KEYS, set(snapshot))
        self.assertEqual("1.0", snapshot["schema_version"])
        self.assertEqual("0.1.0", snapshot["probe_version"])
        self.assertTrue(snapshot["timestamp"].endswith("Z"))
        self.assertEqual([], snapshot["processes"])

    def test_one_failed_collector_degrades_only_its_metric(self) -> None:
        with (
            mock.patch.object(
                probe, "_collect_cpu", side_effect=PermissionError("access denied")
            ),
            mock.patch.object(
                probe,
                "_collect_memory",
                return_value={"total_bytes": 100, "available_bytes": 50},
            ),
            mock.patch.object(
                probe,
                "_collect_disk",
                return_value={"total_bytes": 1000, "free_bytes": 500},
            ),
            mock.patch.object(probe, "_collect_gpu", return_value={"devices": []}),
            mock.patch.object(probe.platform, "system", return_value="Linux"),
        ):
            snapshot = probe.collect_snapshot(sample_seconds=0.1)

        self.assertEqual({}, snapshot["cpu"])
        self.assertEqual(100, snapshot["memory"]["total_bytes"])
        self.assertIn(
            {
                "metric": "cpu.utilization_percent",
                "reason": "access denied",
            },
            snapshot["unavailable"],
        )

    def test_disk_collector_failure_marks_all_disk_byte_metrics_unavailable(
        self,
    ) -> None:
        with (
            mock.patch.object(
                probe,
                "_collect_cpu",
                return_value={"logical_cpus": 8, "utilization_percent": 20.0},
            ),
            mock.patch.object(
                probe,
                "_collect_memory",
                return_value={"total_bytes": 100, "available_bytes": 50},
            ),
            mock.patch.object(
                probe, "_collect_disk", side_effect=PermissionError("disk denied")
            ),
            mock.patch.object(probe, "_collect_gpu", return_value={"devices": []}),
            mock.patch.object(probe.platform, "system", return_value="Linux"),
        ):
            snapshot = probe.collect_snapshot(sample_seconds=0.1)

        disk_errors = {
            item["metric"]: item["reason"]
            for item in snapshot["unavailable"]
            if item["metric"].startswith("disk.")
        }
        self.assertEqual(
            {
                "disk.total_bytes": "disk denied",
                "disk.used_bytes": "disk denied",
                "disk.free_bytes": "disk denied",
            },
            disk_errors,
        )

    def test_missing_windows_tool_degrades_gpu_only(self) -> None:
        unavailable: list[dict[str, str]] = []
        with (
            mock.patch.object(
                probe,
                "_base_gpu_devices",
                side_effect=FileNotFoundError(
                    "no trusted executable candidate for powershell.exe"
                ),
            ),
            mock.patch.object(
                probe,
                "resolve_trusted_executable",
                side_effect=FileNotFoundError(
                    "no trusted executable candidate for nvidia-smi"
                ),
            ),
        ):
            result = probe._collect_gpu("Windows", unavailable)
        self.assertEqual({"devices": []}, result)
        self.assertEqual(
            {
                "gpu.base":
                "no trusted executable candidate for powershell.exe",
                "gpu.nvidia":
                "no trusted executable candidate for nvidia-smi",
            },
            {
                item["metric"]: item["reason"]
                for item in unavailable
            },
        )

    def test_process_command_timeout_degrades_processes_only(self) -> None:
        error_type = getattr(probe, "CommandTimeoutError", None)
        self.assertIsNotNone(error_type)
        unavailable: list[dict[str, str]] = []
        with mock.patch.object(
            probe,
            "run_command",
            side_effect=error_type(
                "diagnostic child timed out after 5.0 seconds"
            ),
        ), mock.patch.object(
            probe,
            "resolve_trusted_executable",
            return_value=Path("/usr/bin/ps"),
        ):
            result = probe._collect_degraded(
                probe._collect_processes,
                ("Darwin",),
                "processes",
                unavailable,
                [],
            )
        self.assertEqual([], result)
        self.assertEqual("processes", unavailable[0]["metric"])
        self.assertIn("timed out", unavailable[0]["reason"])

    def test_successful_empty_process_result_is_not_unavailable(self) -> None:
        with (
            mock.patch.object(
                probe,
                "_collect_cpu",
                return_value={
                    "logical_cpus": 8,
                    "utilization_percent": 20.0,
                    "load_average": {"1m": 0.1, "5m": 0.2, "15m": 0.3},
                },
            ),
            mock.patch.object(
                probe,
                "_collect_memory",
                return_value={"total_bytes": 100, "available_bytes": 50},
            ),
            mock.patch.object(
                probe,
                "_collect_disk",
                return_value={
                    "total_bytes": 1000,
                    "used_bytes": 500,
                    "free_bytes": 500,
                },
            ),
            mock.patch.object(probe, "_collect_gpu", return_value={"devices": []}),
            mock.patch.object(probe, "_collect_processes", return_value=[]),
            mock.patch.object(probe.platform, "system", return_value="Linux"),
        ):
            snapshot = probe.collect_snapshot(
                sample_seconds=0.1,
                include_processes=True,
            )

        self.assertFalse(
            any(item["metric"] == "processes" for item in snapshot["unavailable"])
        )
        self.assertFalse(
            any(item["metric"] == "gpu.devices" for item in snapshot["unavailable"])
        )


class CliTests(unittest.TestCase):
    def run_main(
        self, argv: list[str]
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = probe.main(argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_json_is_written_to_stdout(self) -> None:
        snapshot = sample_snapshot()
        with mock.patch.object(probe, "collect_snapshot", return_value=snapshot):
            result, stdout, stderr = self.run_main(
                ["--format", "json", "--sample-seconds", "0.1"]
            )
        self.assertEqual(0, result)
        self.assertEqual(snapshot, json.loads(stdout))
        self.assertEqual("", stderr)

    def test_text_is_written_to_stdout(self) -> None:
        with mock.patch.object(probe, "collect_snapshot", return_value=sample_snapshot()):
            result, stdout, stderr = self.run_main(["--format", "text"])
        self.assertEqual(0, result)
        for heading in ("CPU", "Memory", "Disk", "GPU", "Recommendation"):
            self.assertIn(heading, stdout)
        self.assertEqual("", stderr)

    @unittest.skipIf(
        os.name == "nt",
        "Windows v0.1 output files fail closed; use stdout",
    )
    def test_output_file_success_does_not_duplicate_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir).resolve(strict=True) / "snapshot.json"
            with mock.patch.object(
                probe, "collect_snapshot", return_value=sample_snapshot()
            ):
                result, stdout, stderr = self.run_main(
                    ["--format", "json", "--output", str(output)]
                )
            self.assertEqual(0, result)
            self.assertEqual("", stdout)
            self.assertEqual(sample_snapshot(), json.loads(output.read_text("utf-8")))
            self.assertEqual("", stderr)

    @unittest.skipIf(
        os.name == "nt",
        "Windows v0.1 output files fail closed; use stdout",
    )
    def test_existing_output_file_is_rejected_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir).resolve(strict=True) / "snapshot.json"
            output.write_text("keep me", encoding="utf-8")
            with mock.patch.object(
                probe, "collect_snapshot", return_value=sample_snapshot()
            ):
                result, stdout, stderr = self.run_main(
                    ["--format", "json", "--output", str(output)]
                )

            self.assertEqual(1, result)
            self.assertEqual("", stdout)
            self.assertIn("already exists", stderr)
            self.assertEqual("keep me", output.read_text(encoding="utf-8"))

    @unittest.skipIf(
        os.name == "nt",
        "Windows v0.1 output files fail closed; use stdout",
    )
    def test_symlink_output_file_is_rejected_without_following(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir).resolve(strict=True)
            target = directory / "target.json"
            target.write_text("keep target", encoding="utf-8")
            output = directory / "snapshot.json"
            try:
                output.symlink_to(target)
            except OSError:
                original_is_symlink = Path.is_symlink

                def simulated_symlink(path: Path) -> bool:
                    return path == output or original_is_symlink(path)

                symlink_patch = mock.patch.object(
                    probe.Path,
                    "is_symlink",
                    autospec=True,
                    side_effect=simulated_symlink,
                )
            else:
                symlink_patch = contextlib.nullcontext()

            with symlink_patch, mock.patch.object(
                probe,
                "collect_snapshot",
                return_value=sample_snapshot(),
            ):
                result, stdout, stderr = self.run_main(
                    ["--format", "json", "--output", str(output)]
                )

            self.assertEqual(1, result)
            self.assertEqual("", stdout)
            self.assertIn("symlink", stderr)
            self.assertEqual("keep target", target.read_text(encoding="utf-8"))

    @unittest.skipIf(
        os.name == "nt",
        "Windows v0.1 output files fail closed; use stdout",
    )
    def test_symlinked_posix_output_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve(strict=True)
            target = root / "target"
            target.mkdir()
            parent = root / "parent"
            parent.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(OSError, "parent"):
                probe._write_output_exclusive(
                    parent / "snapshot.json",
                    "{}\n",
                )

            self.assertFalse((target / "snapshot.json").exists())

    def test_windows_output_file_write_fails_closed_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            probe.platform,
            "system",
            return_value="Windows",
        ):
            output = Path(temporary) / "snapshot.json"
            with self.assertRaisesRegex(OSError, "stdout"):
                probe._write_output_exclusive(output, "{}\n")
            self.assertFalse(output.exists())

    @unittest.skipUnless(
        os.name == "nt",
        "requires Windows junction semantics",
    )
    def test_windows_output_rejects_junction_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            junction = root / "junction"
            result = subprocess.run(
                [
                    os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe"),
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(junction),
                    str(target),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest(
                    "Windows junction creation unavailable: "
                    + (result.stderr.strip() or result.stdout.strip())
                )
            with self.assertRaisesRegex(OSError, "stdout"):
                probe._write_output_exclusive(
                    junction / "snapshot.json",
                    "{}\n",
                )
            self.assertFalse((target / "snapshot.json").exists())

    @unittest.skipUnless(
        os.name == "posix",
        "requires POSIX dir_fd traversal",
    )
    def test_parent_swap_cannot_redirect_posix_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            original_parent = root / "safe"
            original_parent.mkdir()
            moved_parent = root / "safe-held"
            attacker_parent = root / "attacker"
            attacker_parent.mkdir()
            destination = original_parent / "snapshot.json"
            original_open = probe.os.open
            swapped = False

            def swapping_open(
                path: object,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal swapped
                if os.fspath(path) == destination.name and dir_fd is not None:
                    original_parent.rename(moved_parent)
                    original_parent.symlink_to(
                        attacker_parent,
                        target_is_directory=True,
                    )
                    swapped = True
                return original_open(path, flags, mode, dir_fd=dir_fd)

            with mock.patch.object(probe.os, "open", side_effect=swapping_open):
                probe._write_output_exclusive(destination, "{}\n")

            self.assertTrue(swapped, "output was not created relative to a held dirfd")
            self.assertEqual("{}\n", (moved_parent / destination.name).read_text())
            self.assertFalse((attacker_parent / destination.name).exists())

    def test_posix_dir_fd_capability_is_immutable_when_open_is_wrapped(
        self,
    ) -> None:
        expected = (
            os.name == "posix"
            and probe.os.open in probe.os.supports_dir_fd
        )
        with mock.patch.object(probe.os, "open", wraps=probe.os.open):
            self.assertEqual(
                expected,
                probe._POSIX_DIR_FD_OPEN_SUPPORTED,
            )

    def test_invalid_sampling_returns_exit_code_two(self) -> None:
        result, stdout, stderr = self.run_main(["--sample-seconds", "0"])
        self.assertEqual(2, result)
        self.assertEqual("", stdout)
        self.assertIn("sample", stderr.lower())

    @unittest.skipIf(
        os.name == "nt",
        "Windows v0.1 output files fail closed; use stdout",
    )
    def test_unwritable_output_returns_exit_code_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = (
                Path(temp_dir).resolve(strict=True)
                / "missing-parent"
                / "snapshot.json"
            )
            with mock.patch.object(
                probe, "collect_snapshot", return_value=sample_snapshot()
            ):
                result, stdout, stderr = self.run_main(
                    ["--format", "json", "--output", str(output)]
                )
        self.assertEqual(1, result)
        self.assertEqual("", stdout)
        self.assertIn("write", stderr.lower())

    def test_unsupported_platform_returns_three_without_inventing_metrics(self) -> None:
        with mock.patch.object(probe.platform, "system", return_value="Plan9"):
            result, stdout, stderr = self.run_main(["--format", "json"])
        self.assertEqual(3, result)
        self.assertEqual("", stdout)
        self.assertIn("unsupported", stderr.lower())
        self.assertIn("Plan9", stderr)
        self.assertNotIn("cpu", stderr.lower())


if __name__ == "__main__":
    unittest.main()
