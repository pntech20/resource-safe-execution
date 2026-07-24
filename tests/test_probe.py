import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
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
            mock.patch.object(probe.os, "cpu_count", return_value=8),
            mock.patch.object(probe.time, "sleep"),
        ):
            result = probe._collect_cpu("Darwin", 0.1)
        self.assertEqual(30.0, result["utilization_percent"])

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
        with mock.patch.object(probe, "run_command", side_effect=results):
            memory = probe._collect_memory("Darwin")
        self.assertEqual(17_179_869_184, memory["total_bytes"])
        self.assertEqual((100 + 200 + 10) * 16_384, memory["available_bytes"])

    def test_windows_gpu_uses_cim_json_with_bounded_command_wrapper(self) -> None:
        gpu_json = (FIXTURES / "windows-gpu.json").read_text(encoding="utf-8")
        with (
            mock.patch.object(
                probe, "run_command", return_value=probe.CommandResult(0, gpu_json, "")
            ) as command,
            mock.patch.object(probe.shutil, "which", return_value=None),
        ):
            result = probe._collect_gpu("Windows")
        self.assertEqual(2, len(result["devices"]))
        args = command.call_args.args[0]
        self.assertEqual("powershell.exe", args[0])
        self.assertIn("Win32_VideoController", args[-1])

    def test_windows_processes_use_cim_and_privacy_preserving_parser(self) -> None:
        process_json = (FIXTURES / "processes-windows.json").read_text(
            encoding="utf-8"
        )
        with mock.patch.object(
            probe, "run_command", return_value=probe.CommandResult(0, process_json, "")
        ) as command:
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
    def test_run_command_rejects_invalid_timeout_before_starting_process(
        self,
    ) -> None:
        invalid_timeouts = (0, -1, 5.1, float("nan"), float("inf"), "invalid")
        for timeout in invalid_timeouts:
            with self.subTest(timeout=timeout), mock.patch.object(
                probe.subprocess, "run"
            ) as subprocess_run:
                with self.assertRaises(ValueError):
                    probe.run_command([sys.executable, "-V"], timeout_seconds=timeout)
                subprocess_run.assert_not_called()

    def test_run_command_accepts_five_second_binding_maximum(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[sys.executable, "-V"],
            returncode=0,
            stdout="Python",
            stderr="",
        )
        with mock.patch.object(
            probe.subprocess, "run", return_value=completed
        ) as subprocess_run:
            result = probe.run_command(
                [sys.executable, "-V"], timeout_seconds=5.0
            )
        self.assertEqual(0, result.returncode)
        self.assertEqual(5.0, subprocess_run.call_args.kwargs["timeout"])

    def test_run_command_captures_utf8_output_without_a_shell(self) -> None:
        result = probe.run_command(
            [
                sys.executable,
                "-c",
                "import sys; "
                "sys.stdout.buffer.write('resource probe \\u2713'.encode('utf-8'))",
            ],
            timeout_seconds=2.0,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual("resource probe ✓", result.stdout.strip())
        self.assertEqual("", result.stderr)


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

    def test_high_cpu_caps_balanced_to_half_logical_cpus(self) -> None:
        result = probe.build_recommendation(
            {"logical_cpus": 8, "utilization_percent": 75.0},
            {"total_bytes": 100, "available_bytes": 80},
        )
        self.assertEqual(4, result["profiles"]["balanced"]["max_workers"])

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


class SnapshotTests(unittest.TestCase):
    def test_collect_snapshot_rejects_invalid_programmatic_sample_seconds(
        self,
    ) -> None:
        for value in (0, 10.1, float("nan"), float("inf"), "not-a-number", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    probe.collect_snapshot(sample_seconds=value)

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
        with mock.patch.object(
            probe,
            "run_command",
            side_effect=FileNotFoundError("powershell.exe was not found"),
        ):
            result = probe._collect_degraded(
                probe._collect_gpu,
                ("Windows",),
                "gpu.devices",
                unavailable,
                {"devices": []},
            )
        self.assertEqual({"devices": []}, result)
        self.assertEqual("gpu.devices", unavailable[0]["metric"])
        self.assertIn("powershell.exe", unavailable[0]["reason"])

    def test_process_command_timeout_degrades_processes_only(self) -> None:
        unavailable: list[dict[str, str]] = []
        with mock.patch.object(
            probe,
            "run_command",
            side_effect=subprocess.TimeoutExpired(["ps"], 5.0),
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

    def test_output_file_success_does_not_duplicate_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "snapshot.json"
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

    def test_invalid_sampling_returns_exit_code_two(self) -> None:
        result, stdout, stderr = self.run_main(["--sample-seconds", "0"])
        self.assertEqual(2, result)
        self.assertEqual("", stdout)
        self.assertIn("sample", stderr.lower())

    def test_unwritable_output_returns_exit_code_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "missing-parent" / "snapshot.json"
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
