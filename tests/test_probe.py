import contextlib
import importlib.util
import io
import json
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
