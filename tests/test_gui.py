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
        from tkinter.ttk import Treeview

        window = next(child for child in self.root.winfo_children() if isinstance(child, Toplevel))
        table = next(child for child in window.winfo_children() if isinstance(child, Treeview))
        viewer = next(child for child in window.winfo_children() if isinstance(child, Text))
        self.assertEqual(len(table.get_children()), 1)
        self.assertIn("ESCALATED FAILURE", viewer.get("1.0", "end"))


if __name__ == "__main__":
    unittest.main()
