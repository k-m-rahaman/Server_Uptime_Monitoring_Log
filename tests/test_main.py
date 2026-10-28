"""Behavior tests for the simulated server monitor (standard library only)."""

import contextlib
import io
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import format_report, monitor_server


class MonitorServerTests(unittest.TestCase):
    def test_threshold_boundaries_are_classified_correctly(self):
        report = monitor_server(days=5, ping_values=[0, 100, 101, 300, 301])

        self.assertEqual(
            [entry["status"] for entry in report["entries"]],
            ["HEALTHY", "HEALTHY", "MINOR LAG", "MINOR LAG", "CRITICAL FAILURE"],
        )
        self.assertEqual(report["healthy_days"], 2)
        self.assertEqual(report["lag_days"], 2)
        self.assertEqual(report["critical_days"], 1)

    def test_minor_lag_continues_to_the_next_day(self):
        report = monitor_server(days=3, ping_values=[150, 250, 45])

        self.assertEqual([entry["day"] for entry in report["entries"]], [1, 2, 3])
        self.assertEqual(report["entries"][-1]["status"], "HEALTHY")
        self.assertEqual(report["lag_days"], 2)
        self.assertEqual(report["healthy_days"], 1)
        self.assertFalse(report["stopped_early"])

    def test_critical_failure_is_logged_and_later_readings_are_not_consumed(self):
        def readings():
            yield 50
            yield 301
            self.fail("The monitor consumed a reading after its critical failure.")

        report = monitor_server(days=7, ping_values=readings())

        self.assertEqual(len(report["entries"]), 2)
        self.assertEqual(report["entries"][-1]["ping_ms"], 301)
        self.assertEqual(report["entries"][-1]["status"], "CRITICAL FAILURE")
        self.assertEqual(report["requested_days"], 7)
        self.assertTrue(report["stopped_early"])
        self.assertEqual(report["critical_days"], 1)

    def test_critical_failure_on_the_last_day_is_not_an_early_stop(self):
        report = monitor_server(days=2, ping_values=[50, 350])

        self.assertEqual(len(report["entries"]), 2)
        self.assertEqual(report["critical_days"], 1)
        self.assertFalse(report["stopped_early"])

    def test_all_healthy_days_complete_the_requested_period(self):
        report = monitor_server(days=3, ping_values=[25, 75, 100])

        self.assertEqual(report["healthy_days"], 3)
        self.assertEqual(report["lag_days"], 0)
        self.assertEqual(report["critical_days"], 0)
        self.assertEqual(len(report["entries"]), 3)
        self.assertFalse(report["stopped_early"])

    def test_demo_readings_stop_on_day_six(self):
        report = monitor_server(days=7, ping_values=[45, 160, 72, 100, 300, 301, 55])

        self.assertEqual(len(report["entries"]), 6)
        self.assertEqual(report["healthy_days"], 3)
        self.assertEqual(report["lag_days"], 2)
        self.assertEqual(report["critical_days"], 1)
        self.assertTrue(report["stopped_early"])

    def test_seed_repeats_the_same_simulation(self):
        self.assertEqual(monitor_server(days=10, seed=42), monitor_server(days=10, seed=42))

    def test_random_pings_stay_in_range_and_have_matching_statuses(self):
        for seed in [0, 1, 2, 3, 5, 42, 123]:
            with self.subTest(seed=seed):
                report = monitor_server(days=1, seed=seed)
                entry = report["entries"][0]
                ping_ms = entry["ping_ms"]

                self.assertIs(type(ping_ms), int)
                self.assertGreaterEqual(ping_ms, 20)
                self.assertLessEqual(ping_ms, 350)
                valid_ranges = {
                    "HEALTHY": (20, 100),
                    "MINOR LAG": (101, 300),
                    "CRITICAL FAILURE": (301, 350),
                }
                self.assertIn(entry["status"], valid_ranges)
                lower, upper = valid_ranges[entry["status"]]
                self.assertTrue(lower <= ping_ms <= upper)

    def test_seeded_monitor_does_not_change_global_random_state(self):
        initial_state = random.getstate()

        monitor_server(days=7, seed=42)

        self.assertEqual(random.getstate(), initial_state)

    def test_days_must_be_a_positive_integer(self):
        for invalid_days in [0, -1, 1.5, "7", True, None]:
            with self.subTest(days=invalid_days):
                with self.assertRaises(ValueError):
                    monitor_server(days=invalid_days, ping_values=[50])

    def test_ping_values_must_be_nonnegative_integers(self):
        for invalid_ping in [-1, 1.5, "100", True, None]:
            with self.subTest(ping_ms=invalid_ping):
                with self.assertRaises(ValueError):
                    monitor_server(days=1, ping_values=[invalid_ping])

    def test_missing_readings_before_completion_raise_an_error(self):
        with self.assertRaises(ValueError):
            monitor_server(days=3, ping_values=[50, 150])

    def test_monitor_returns_data_without_printing(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            report = monitor_server(days=1, ping_values=[50])

        self.assertEqual(output.getvalue(), "")
        self.assertEqual(report["healthy_days"], 1)

    def test_report_includes_checked_days_and_no_rows_after_failure(self):
        report = monitor_server(days=7, ping_values=[45, 160, 72, 100, 300, 301, 55])

        text = format_report(report)

        self.assertIsInstance(text, str)
        self.assertIn("Day 001", text)
        self.assertIn("Day 006", text)
        self.assertNotIn("Day 007", text)
        self.assertIn("CRITICAL FAILURE", text)
        self.assertIn("MINOR LAG", text)
        self.assertIn("50.00%", text)


class CommandLineTests(unittest.TestCase):
    script = Path(__file__).resolve().parents[1] / "main.py"

    def test_demo_saves_the_same_report_that_it_prints(self):
        with tempfile.TemporaryDirectory() as directory:
            log_file = Path(directory) / "saved" / "demo.log"
            result = subprocess.run(
                [sys.executable, str(self.script), "--demo", "--log-file", str(log_file)],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            saved_report = log_file.read_text(encoding="utf-8")
            self.assertEqual(result.stdout, saved_report + f"\nLog saved to: {log_file}\n")
            self.assertIn("Day 006", saved_report)
            self.assertNotIn("Day 007", saved_report)
            self.assertIn("50.00%", saved_report)

    def test_invalid_days_are_rejected_before_a_log_is_written(self):
        for arguments in [["--days", "0"], ["--demo", "--days", "8"]]:
            with self.subTest(arguments=arguments):
                with tempfile.TemporaryDirectory() as directory:
                    log_file = Path(directory) / "saved" / "invalid.log"
                    result = subprocess.run(
                        [sys.executable, str(self.script), *arguments,
                         "--log-file", str(log_file)],
                        cwd=directory,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    self.assertEqual(result.returncode, 2)
                    self.assertIn("error:", result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertFalse(log_file.exists())
                    self.assertFalse(log_file.parent.exists())


if __name__ == "__main__":
    unittest.main()
