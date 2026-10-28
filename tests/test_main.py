"""Behavior tests for the simulated server monitor (standard library only)."""

import contextlib
import io
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import format_report, monitor_server, save_run_history


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

    def test_three_consecutive_lag_spikes_escalate_and_do_not_read_next_day(self):
        def readings():
            yield from [65, 180, 240, 280]
            self.fail("An escalated failure must stop the for loop.")

        report = monitor_server(days=7, ping_values=readings())
        self.assertEqual(len(report["entries"]), 4)
        self.assertEqual(report["entries"][-1]["status"], "ESCALATED FAILURE")
        self.assertEqual([e["action"] for e in report["entries"]],
                         ["record", "continue", "continue", "break"])
        self.assertEqual((report["healthy_days"], report["lag_days"], report["critical_days"]), (1, 2, 1))
        self.assertEqual(report["failure_type"], "lag_escalation")
        self.assertEqual(report["max_lag_streak"], 3)
        self.assertTrue(report["stopped_early"])
        self.assertIn("3 consecutive", report["stop_reason"])

    def test_healthy_day_resets_the_lag_streak(self):
        report = monitor_server(days=6, ping_values=[180, 240, 70, 180, 240, 80])
        self.assertEqual([e["lag_streak"] for e in report["entries"]], [1, 2, 0, 1, 2, 0])
        self.assertEqual(report["max_lag_streak"], 2)
        self.assertEqual(report["critical_days"], 0)
        self.assertIsNone(report["failure_type"])

    def test_critical_ping_takes_priority_over_an_existing_lag_streak(self):
        report = monitor_server(days=7, ping_values=[180, 240, 301])
        self.assertEqual(report["entries"][-1]["status"], "CRITICAL FAILURE")
        self.assertEqual(report["failure_type"], "critical_ping")
        self.assertEqual(report["max_lag_streak"], 2)
        self.assertIn("301 ms", report["stop_reason"])

    def test_each_scenario_generates_readings_within_its_range(self):
        expected_ranges = {"stable": (20, 140), "busy": (60, 320), "unstable": (80, 450)}
        for scenario, (low, high) in expected_ranges.items():
            for seed in [0, 1, 7, 42, 123]:
                with self.subTest(scenario=scenario, seed=seed):
                    report = monitor_server(days=10, seed=seed, scenario=scenario)
                    self.assertTrue(all(low <= e["ping_ms"] <= high for e in report["entries"]))
                    self.assertEqual(report["scenario"], scenario)

    def test_unknown_scenario_is_rejected(self):
        with self.assertRaises(ValueError):
            monitor_server(scenario="missing")

    def test_failure_on_final_day_is_counted_without_claiming_days_were_skipped(self):
        report = monitor_server(days=3, ping_values=[150, 200, 250])
        self.assertFalse(report["stopped_early"])
        self.assertEqual(report["critical_days"], 1)
        self.assertEqual(report["failure_type"], "lag_escalation")


class HistoryTests(unittest.TestCase):
    def test_each_saved_run_has_a_separate_complete_record_and_readable_log(self):
        with tempfile.TemporaryDirectory() as directory:
            report = monitor_server(days=2, ping_values=[45, 180])
            first = save_run_history(report, directory)
            second = save_run_history(report, directory)
            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 2)
            for path in [first, second]:
                record = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(record["entries"], report["entries"])
                self.assertIn("created_at", record)
                self.assertEqual(path.with_suffix(".txt").read_text(encoding="utf-8"),
                                 format_report(report) + "\n")


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

    def test_lag_demo_saves_its_failure_reason_and_a_history_record(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(self.script), "--demo-lag"], cwd=directory,
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ESCALATED FAILURE", result.stdout)
            self.assertNotIn("Day 005", result.stdout)
            records = list((Path(directory) / "logs" / "history").glob("*.json"))
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text())
            self.assertEqual(record["scenario"], "busy")
            self.assertEqual(record["failure_type"], "lag_escalation")

    def test_seed_cannot_be_combined_with_a_fixed_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(self.script), "--demo-lag", "--seed", "42"],
                cwd=directory, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--seed is for random mode", result.stderr)
            self.assertFalse((Path(directory) / "logs").exists())


if __name__ == "__main__":
    unittest.main()
