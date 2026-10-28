"""Optional desktop integration checks: set RUN_GUI_TESTS=1 on a GUI machine."""

import json
import os
import tempfile
import unittest
from pathlib import Path


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
        self.run_demo("Demo: repeated lag")
        self.assertEqual(len(self.app.table.get_children()), 4)
        self.assertEqual([value.get() for value in self.app.stats.values()], ["4", "1", "2", "1"])
        self.assertIn("3 consecutive", self.app.reason.get())
        self.app.notebook.select(self.app.charts)
        self.root.update()
        self.assertGreater(len(self.app.timeline.find_all()), 5)
        self.assertEqual(str(self.app.export_button["state"]), "normal")
        paths = list(Path(self.directory.name).glob("*.json"))
        self.assertEqual(len(paths), 1)
        self.assertEqual(json.loads(paths[0].read_text())["failure_type"], "lag_escalation")

    def test_rerunning_replaces_current_table_and_preserves_both_history_records(self):
        self.run_demo("Demo: critical failure")
        self.assertEqual(len(self.app.table.get_children()), 6)
        self.run_demo("Demo: repeated lag")
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

    def test_results_and_charts_are_available_as_separate_tabs(self):
        self.assertEqual(self.app.notebook.select(), str(self.app.log_box))
        self.app.toggle_charts()
        self.root.update()
        self.assertEqual(self.app.notebook.select(), str(self.app.charts))
        self.app.toggle_charts()
        self.root.update()
        self.assertEqual(self.app.notebook.select(), str(self.app.log_box))

    def test_selecting_a_day_explains_its_python_control_flow(self):
        self.run_demo("Demo: critical failure")
        for day, expected in [(2, "continue"), (3, "reset"), (6, "break")]:
            with self.subTest(day=day):
                self.app.table.selection_set(str(day))
                self.root.update()
                self.assertIn(f"Day {day}:", self.app.detail.get())
                self.assertIn(expected, self.app.detail.get())

    def test_recommended_demo_and_optional_random_seed_controls(self):
        self.assertEqual(self.app.mode.get(), "Demo: critical failure")
        self.assertEqual(str(self.app.day_box["state"]), "disabled")
        self.app.mode.set("Random readings")
        self.app.update_setup()
        self.assertEqual(str(self.app.day_box["state"]), "normal")
        self.assertEqual(self.app.scenario.get(), "Stable Network")
        self.app.seed_enabled.set(True)
        self.app.toggle_seed()
        self.app.seed.set("42")
        self.app.start_run()
        self.app.finish_playback()
        self.assertEqual(self.app.report["seed"], 42)

    def test_history_window_opens_saved_log(self):
        self.run_demo("Demo: repeated lag")
        self.app.show_history()
        self.root.update()
        from tkinter import Toplevel, Text
        from tkinter.ttk import Treeview

        window = next(child for child in self.root.winfo_children() if isinstance(child, Toplevel))
        table = next(child for child in window.winfo_children() if isinstance(child, Treeview))
        viewer = next(child for child in window.winfo_children() if isinstance(child, Text))
        self.assertEqual(len(table.get_children()), 1)
        self.assertIn("ESCALATED FAILURE", viewer.get("1.0", "end"))


if __name__ == "__main__":
    unittest.main()
