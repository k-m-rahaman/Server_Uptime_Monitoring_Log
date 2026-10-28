"""Behavior tests for the simulated server monitor (standard library only)."""

import contextlib
import csv
import io
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import (comparison_rows, export_csv, format_report, iter_monitor,
                  monitor_server, report_statistics, save_run_history)


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
    def test_saved_custom_run_preserves_its_rules_and_statistics(self):
        report = monitor_server(days=4, ping_values=[25, 75, 210],
                                healthy_limit=50, critical_limit=200, lag_limit=2)
        with tempfile.TemporaryDirectory() as directory:
            path = save_run_history(report, directory)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual((saved["healthy_limit"], saved["critical_limit"], saved["lag_limit"]),
                         (50, 200, 2))
        self.assertEqual(saved["highest_ping_ms"], 210)
        self.assertAlmostEqual(saved["average_ping_ms"], 310 / 3)

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


class TeachingAndThresholdTests(unittest.TestCase):
    def test_step_iterator_reads_only_the_next_day_and_returns_a_final_report(self):
        consumed = []

        def readings():
            for ping in [40, 150, 320]:
                consumed.append(ping)
                yield ping
            self.fail("Teaching mode read a day after its failure.")

        iterator = iter_monitor(days=7, ping_values=readings())
        self.assertEqual(consumed, [])
        for expected_ping, expected_highlight in [(40, "for"), (150, "continue"), (320, "break")]:
            entry = next(iterator)
            self.assertEqual(entry["ping_ms"], expected_ping)
            self.assertEqual(entry["highlight"], expected_highlight)
            self.assertIsInstance(entry["explanation"], str)
            self.assertTrue(entry["explanation"].strip())
            self.assertEqual(len(consumed), entry["day"])

        with self.assertRaises(StopIteration) as stopped:
            next(iterator)
        report = stopped.exception.value
        self.assertEqual(len(report["entries"]), 3)
        self.assertEqual(report["failure_type"], "critical_ping")
        self.assertEqual(report["healthy_days"], 1)
        self.assertTrue(report["stopped_early"])
        self.assertEqual(consumed, [40, 150, 320])

    def test_last_healthy_step_completes_without_consuming_an_extra_reading(self):
        def readings():
            yield 25
            yield 50
            self.fail("The iterator requested an unplanned third day.")

        iterator = iter_monitor(days=2, ping_values=readings())
        self.assertEqual(next(iterator)["day"], 1)
        self.assertEqual(next(iterator)["day"], 2)
        with self.assertRaises(StopIteration) as stopped:
            next(iterator)
        self.assertEqual(stopped.exception.value["healthy_days"], 2)
        self.assertFalse(stopped.exception.value["stopped_early"])

    def test_custom_threshold_boundaries_change_classification(self):
        report = monitor_server(days=5, ping_values=[0, 50, 51, 200, 201],
                                healthy_limit=50, critical_limit=200, lag_limit=4)
        self.assertEqual([entry["status"] for entry in report["entries"]],
                         ["HEALTHY", "HEALTHY", "MINOR LAG", "MINOR LAG", "CRITICAL FAILURE"])
        self.assertEqual((report["healthy_limit"], report["critical_limit"], report["lag_limit"]),
                         (50, 200, 4))
        self.assertIn("200", report["stop_reason"])

    def test_custom_lag_limit_stops_on_the_selected_consecutive_day(self):
        iterator = iter_monitor(days=5, ping_values=[60, 80],
                                healthy_limit=50, critical_limit=200, lag_limit=2)
        self.assertEqual(next(iterator)["action"], "continue")
        final_entry = next(iterator)
        self.assertEqual(final_entry["status"], "ESCALATED FAILURE")
        self.assertEqual(final_entry["highlight"], "break")
        with self.assertRaises(StopIteration) as stopped:
            next(iterator)
        self.assertEqual(stopped.exception.value["max_lag_streak"], 2)
        self.assertEqual(stopped.exception.value["critical_days"], 1)

    def test_invalid_thresholds_are_rejected(self):
        cases = [
            {"healthy_limit": -1}, {"healthy_limit": True}, {"healthy_limit": 10.5},
            {"critical_limit": False}, {"critical_limit": "300"},
            {"healthy_limit": 300, "critical_limit": 300},
            {"healthy_limit": 400, "critical_limit": 300},
            {"lag_limit": 0}, {"lag_limit": -1}, {"lag_limit": True}, {"lag_limit": 1.5},
        ]
        for settings in cases:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    monitor_server(days=1, ping_values=[25], **settings)


class StatisticsAndExportTests(unittest.TestCase):
    def test_statistics_include_the_failure_but_exclude_unchecked_readings(self):
        report = monitor_server(days=5, ping_values=[40, 150, 320, 900, 999])
        stats = report_statistics(report)
        self.assertEqual(stats["checked_days"], 3)
        self.assertEqual(stats["average_ping_ms"], 170)
        self.assertEqual(stats["highest_ping_ms"], 320)
        self.assertEqual(stats["max_lag_streak"], 1)
        self.assertAlmostEqual(stats["healthy_rate"], 100 / 3)
        self.assertEqual(report["average_ping_ms"], 170)
        self.assertEqual(report["highest_ping_ms"], 320)

    def test_empty_partial_report_has_no_ping_statistics(self):
        stats = report_statistics({"entries": []})
        self.assertEqual(stats["checked_days"], 0)
        self.assertIsNone(stats["average_ping_ms"])
        self.assertIsNone(stats["highest_ping_ms"])
        self.assertEqual(stats["max_lag_streak"], 0)
        self.assertEqual(stats["healthy_rate"], 0)

    def test_legacy_saved_report_remains_readable_and_exportable(self):
        report = monitor_server(days=3, ping_values=[25, 150, 320])
        for key in ["healthy_limit", "critical_limit", "lag_limit", "average_ping_ms", "highest_ping_ms"]:
            report.pop(key)
        for entry in report["entries"]:
            entry.pop("explanation")
            entry.pop("highlight")
        text = format_report(report)
        self.assertIn("CRITICAL FAILURE", text)
        self.assertIn("Average ping", text)
        self.assertIn("Highest ping", text)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.csv"
            export_csv(report, path)
            with path.open(encoding="utf-8", newline="") as saved:
                row = next(csv.DictReader(saved))
            self.assertEqual((row["healthy_limit"], row["critical_limit"], row["lag_limit"]),
                             ("100", "300", "3"))

    def test_csv_contains_only_checked_days_and_their_rule_settings(self):
        report = monitor_server(days=4, ping_values=[25, 75, 210, 999],
                                healthy_limit=50, critical_limit=200, lag_limit=3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "readings.csv"
            export_csv(report, path)
            with path.open(encoding="utf-8", newline="") as saved:
                reader = csv.DictReader(saved)
                rows = list(reader)
                self.assertEqual(reader.fieldnames,
                                 ["day", "ping_ms", "status", "lag_streak", "action",
                                  "healthy_limit", "critical_limit", "lag_limit"])
        self.assertEqual([row["day"] for row in rows], ["1", "2", "3"])
        self.assertEqual(rows[-1]["ping_ms"], "210")
        self.assertEqual(rows[-1]["action"], "break")
        self.assertTrue(all((row["healthy_limit"], row["critical_limit"], row["lag_limit"]) ==
                            ("50", "200", "3") for row in rows))

    def test_empty_csv_still_has_a_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.csv"
            export_csv({"entries": []}, path)
            with path.open(encoding="utf-8", newline="") as saved:
                reader = csv.DictReader(saved)
                self.assertEqual(list(reader), [])
                self.assertIn("ping_ms", reader.fieldnames)

    def test_comparison_shows_differences_in_results_and_thresholds(self):
        first = monitor_server(days=4, ping_values=[25, 75, 210],
                               healthy_limit=50, critical_limit=200, lag_limit=3)
        second = monitor_server(days=2, ping_values=[30, 40],
                                healthy_limit=100, critical_limit=300, lag_limit=4)
        rows = comparison_rows(first, second)
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 3 and all(isinstance(value, str) for value in row)
                            for row in rows))
        metrics = {row[0].casefold(): row[1:] for row in rows}
        for label, a, b in [("healthy limit", "50", "100"),
                            ("critical limit", "200", "300"), ("lag limit", "3", "4"),
                            ("highest ping", "210", "40")]:
            self.assertIn(a, metrics[label][0])
            self.assertIn(b, metrics[label][1])
        self.assertNotEqual(*metrics["average ping"])
        self.assertTrue(any("critical" in value.casefold() for row in rows for value in row[1:]))


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

    def test_custom_cli_rules_are_saved_and_csv_matches_the_run(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "run.csv"
            result = subprocess.run(
                [sys.executable, str(self.script), "--days", "3", "--seed", "42",
                 "--healthy-limit", "50", "--critical-limit", "200", "--lag-limit", "2",
                 "--csv-file", str(csv_path)],
                cwd=directory, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            records = list((Path(directory) / "logs" / "history").glob("*.json"))
            self.assertEqual(len(records), 1)
            report = json.loads(records[0].read_text(encoding="utf-8"))
            self.assertEqual((report["healthy_limit"], report["critical_limit"], report["lag_limit"]),
                             (50, 200, 2))
            with csv_path.open(encoding="utf-8", newline="") as saved:
                rows = list(csv.DictReader(saved))
            self.assertEqual(len(rows), len(report["entries"]))
            self.assertEqual([int(row["ping_ms"]) for row in rows],
                             [entry["ping_ms"] for entry in report["entries"]])

    def test_invalid_custom_cli_rules_create_no_output(self):
        for settings in [["--healthy-limit", "300", "--critical-limit", "100"],
                         ["--lag-limit", "0"]]:
            with self.subTest(settings=settings):
                with tempfile.TemporaryDirectory() as directory:
                    result = subprocess.run(
                        [sys.executable, str(self.script), *settings, "--csv-file", "run.csv"],
                        cwd=directory, capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("error:", result.stderr)
                    self.assertFalse((Path(directory) / "logs").exists())
                    self.assertFalse((Path(directory) / "run.csv").exists())


if __name__ == "__main__":
    unittest.main()
