"""Optional desktop integration checks: set RUN_GUI_TESTS=1 on a GUI machine."""

import json
import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


@unittest.skipUnless(os.environ.get("RUN_GUI_TESTS") == "1", "desktop checks require RUN_GUI_TESTS=1")
class DesktopTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from gui import MonitorApp

        self.directory = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.app = MonitorApp(self.root, history_dir=self.directory.name)
        self.root.update()

    def tearDown(self):
        self.app.close()
        self.directory.cleanup()

    def run_demo(self, mode):
        self.app.mode.set(mode)
        self.app.update_setup()
        self.app.start_run()
        self.assertTrue(self.app.running)
        self.app.finish_playback()
        self.root.update()
        self.assertFalse(self.app.running)

    def test_lag_demo_updates_table_chart_summary_and_saved_history(self):
        self.run_demo("Lag escalation demo")
        self.assertEqual(len(self.app.table.get_children()), 4)
        self.assertEqual([value.get() for value in self.app.stats.values()], ["04", "01", "02", "01"])
        self.assertIn("3 consecutive", self.app.reason.get())
        self.assertGreater(len(self.app.timeline.find_all()), 5)
        self.assertEqual(str(self.app.export_button["state"]), "normal")
        paths = list(Path(self.directory.name).glob("*.json"))
        self.assertEqual(len(paths), 1)
        self.assertEqual(json.loads(paths[0].read_text())["failure_type"], "lag_escalation")

    def test_rerunning_replaces_current_table_and_preserves_both_history_records(self):
        self.run_demo("Critical failure demo")
        self.assertEqual(len(self.app.table.get_children()), 6)
        self.run_demo("Lag escalation demo")
        self.assertEqual(len(self.app.table.get_children()), 4)
        self.assertEqual(len(list(Path(self.directory.name).glob("*.json"))), 2)

    def test_status_and_run_controls_fit_inside_the_window(self):
        # Check the recommended desktop size, independent of CI monitor size.
        self.root.geometry("1220x740")
        self.root.update()
        for widget in [self.app.reason_label, self.app.progress, self.app.run_button]:
            with self.subTest(widget=widget):
                top = widget.winfo_rooty() - self.root.winfo_rooty()
                self.assertGreaterEqual(top, 0)
                self.assertLessEqual(top + widget.winfo_height(), self.root.winfo_height())
        self.assertGreaterEqual(self.app.table.winfo_height(), 85)

    def test_expand_log_makes_more_rows_visible_and_can_restore_charts(self):
        before = self.app.table.winfo_height()
        self.app.toggle_charts()
        self.root.update()
        self.assertGreater(self.app.table.winfo_height(), before)
        self.assertFalse(self.app.charts_visible)
        self.app.toggle_charts()
        self.root.update()
        self.assertTrue(self.app.charts_visible)

    def test_history_window_opens_saved_log(self):
        self.run_demo("Lag escalation demo")
        self.app.show_history()
        self.root.update()
        from tkinter import Toplevel, Text

        window = next(child for child in self.root.winfo_children() if isinstance(child, Toplevel))
        table = self.app.history_table
        viewer = next(child for child in window.winfo_children() if isinstance(child, Text))
        self.assertEqual(len(table.get_children()), 1)
        self.assertIn("ESCALATED FAILURE", viewer.get("1.0", "end"))

    def test_teaching_mode_advances_one_actual_day_and_finishes_on_the_break_step(self):
        import gui

        visited = []
        real_iterator = gui.iter_monitor

        def tracked_iterator(*args, **kwargs):
            iterator = real_iterator(*args, **kwargs)
            while True:
                try:
                    entry = next(iterator)
                except StopIteration as stopped:
                    return stopped.value
                visited.append(entry["day"])
                yield entry

        self.app.mode.set("Critical failure demo")
        self.app.update_setup()
        self.app.teaching_mode.set(True)
        self.app.toggle_teaching()
        with mock.patch("gui.iter_monitor", side_effect=tracked_iterator):
            self.app.start_run()
            self.assertTrue(self.app.running)
            self.assertEqual(visited, [])
            self.assertEqual(self.app.visible_entries, [])
            self.assertEqual(list(Path(self.directory.name).glob("*.json")), [])
            for day in range(1, 7):
                self.app.next_day()
                self.assertEqual(visited, list(range(1, day + 1)))
                self.assertEqual(len(self.app.visible_entries), day)
                self.assertEqual(self.app.highlighted_action, self.app.visible_entries[-1]["highlight"])
                if day < 6:
                    self.assertTrue(self.app.running)
            self.assertFalse(self.app.running)
            self.assertEqual(self.app.visible_entries[1]["highlight"], "continue")
            self.assertEqual(self.app.visible_entries[-1]["highlight"], "break")
            self.assertEqual(self.app.report["critical_days"], 1)
            self.assertEqual(len(list(Path(self.directory.name).glob("*.json"))), 1)
            self.app.next_day()
            self.assertEqual(visited, [1, 2, 3, 4, 5, 6])

    def test_teaching_mode_finishes_on_the_last_planned_day_without_an_extra_click(self):
        self.app.days.set("1")
        self.app.seed.set("42")
        self.app.teaching_mode.set(True)
        self.app.toggle_teaching()
        self.app.start_run()
        self.assertTrue(self.app.running)
        self.app.next_day()
        self.assertFalse(self.app.running)
        self.assertEqual(len(self.app.report["entries"]), 1)
        self.assertEqual(self.app.report["requested_days"], 1)
        self.assertFalse(self.app.report["stopped_early"])

    def test_custom_rules_update_results_statistics_and_reject_invalid_changes(self):
        self.app.apply_thresholds(80, 250, 2)
        with self.assertRaises(ValueError):
            self.app.apply_thresholds(300, 100, 0)
        self.assertEqual((self.app.healthy_limit.get(), self.app.critical_limit.get(),
                          self.app.lag_limit.get()), ("80", "250", "2"))
        self.run_demo("Critical failure demo")
        report = self.app.report
        self.assertEqual(len(report["entries"]), 5)
        self.assertEqual((report["healthy_days"], report["lag_days"], report["critical_days"]),
                         (2, 2, 1))
        self.assertAlmostEqual(report["average_ping_ms"], 135.4)
        self.assertEqual(report["highest_ping_ms"], 300)
        self.assertIn("135.4", self.app.ping_metrics.get())
        self.assertIn("300", self.app.ping_metrics.get())
        self.assertIn("1", self.app.lag_metrics.get())

    def test_csv_export_button_writes_the_checked_rows(self):
        self.run_demo("Lag escalation demo")
        path = Path(self.directory.name) / "export.csv"
        with mock.patch("gui.filedialog.asksaveasfilename", return_value=str(path)):
            self.app.export_csv_log()
        with path.open(encoding="utf-8", newline="") as saved:
            rows = list(csv.DictReader(saved))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[-1]["status"], "ESCALATED FAILURE")
        self.assertEqual(rows[-1]["action"], "break")
        self.assertEqual(rows[-1]["lag_limit"], "3")

    def test_history_comparison_requires_two_runs_and_displays_both(self):
        self.run_demo("Critical failure demo")
        self.run_demo("Lag escalation demo")
        self.app.show_history()
        self.root.update()
        table = self.app.history_table
        items = table.get_children()
        self.assertEqual(len(items), 2)
        table.selection_set(items[:1])
        self.root.update()
        self.assertEqual(str(self.app.history_compare_button["state"]), "disabled")
        table.selection_set(items)
        self.root.update()
        self.assertEqual(str(self.app.history_compare_button["state"]), "normal")
        self.app.history_compare_button.invoke()
        self.root.update()
        window = next(child for child in self.root.winfo_children()
                      if hasattr(child, "comparison_table"))
        rows = {window.comparison_table.item(item, "values")[0]:
                window.comparison_table.item(item, "values")[1:]
                for item in window.comparison_table.get_children()}
        self.assertEqual(set(rows["Checked days"]), {"4", "6"})
        self.assertIn("Average ping", rows)
        self.assertIn("Stop reason", rows)

    def test_history_skips_malformed_records_and_opens_legacy_comparison(self):
        from main import format_report, monitor_server

        legacy = monitor_server(days=3, ping_values=[25, 150, 320])
        for key in ["healthy_limit", "critical_limit", "lag_limit", "average_ping_ms",
                    "highest_ping_ms", "scenario", "reading_source", "healthy_days",
                    "lag_days", "critical_days"]:
            legacy.pop(key)
        for entry in legacy["entries"]:
            entry.pop("explanation")
            entry.pop("highlight")

        malformed = [[], {}, {**legacy, "healthy_limit": 400, "critical_limit": 300},
                     {**legacy, "scenario": "unknown"}]
        wrong_status = json.loads(json.dumps(legacy))
        wrong_status["entries"][0]["status"] = "UNKNOWN STATUS"
        malformed.append(wrong_status)
        wrong_reading = json.loads(json.dumps(legacy))
        wrong_reading["entries"][0]["ping_ms"] = "25"
        malformed.append(wrong_reading)
        directory = Path(self.directory.name)
        (directory / "legacy.json").write_text(json.dumps(legacy), encoding="utf-8")
        (directory / "broken.json").write_text("{invalid json", encoding="utf-8")
        for index, record in enumerate(malformed):
            (directory / f"invalid_{index}.json").write_text(json.dumps(record), encoding="utf-8")

        records = self.app.load_history_records()
        self.assertEqual(len(records), 1)
        restored = records[0]
        self.assertEqual(restored["scenario"], "stable")
        self.assertEqual((restored["healthy_days"], restored["lag_days"], restored["critical_days"]),
                         (1, 1, 1))
        self.assertIn("Average ping", format_report(restored))
        self.app.show_history()
        self.root.update()
        self.assertEqual(len(self.app.history_table.get_children()), 1)
        comparison = self.app.show_comparison(restored, monitor_server(days=2, ping_values=[30, 40]))
        rows = {comparison.comparison_table.item(item, "values")[0]:
                comparison.comparison_table.item(item, "values")[1:]
                for item in comparison.comparison_table.get_children()}
        self.assertEqual(rows["Checked days"], ("3", "2"))
        self.assertEqual(rows["Healthy limit"], ("100 ms", "100 ms"))


if __name__ == "__main__":
    unittest.main()
