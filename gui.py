"""Tkinter desktop interface. All simulation decisions live in main.py."""

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from main import (DEMO_PINGS, LAG_DEMO_PINGS, SCENARIOS, format_report,
                  monitor_server, save_run_history)


BG = "#f2f5fa"
PANEL = "#ffffff"
BORDER = "#d8e1ed"
TEXT = "#172b44"
MUTED = "#52677e"
TEAL = "#14745a"
AMBER = "#8c5c08"
RED = "#b62e43"
BLUE = "#285bc5"
COLORS = {"HEALTHY": TEAL, "MINOR LAG": AMBER,
          "CRITICAL FAILURE": RED, "ESCALATED FAILURE": RED}
BASE_DIR = Path(__file__).resolve().parent
HISTORY_DIR = BASE_DIR / "logs" / "history"
MODES = ["Random readings", "Demo: critical failure", "Demo: repeated lag"]
FRIENDLY_STATUS = {"HEALTHY": "Healthy", "MINOR LAG": "Minor lag",
                   "CRITICAL FAILURE": "Critical failure",
                   "ESCALATED FAILURE": "Repeated lag: stopped"}


def label(parent, text="", size=10, color=TEXT, bold=False, **kwargs):
    return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                    font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)


def button(parent, text, command, primary=False):
    return tk.Button(parent, text=text, command=command,
                     bg=BLUE if primary else BG,
                     fg=PANEL if primary else TEXT,
                     activebackground="#204a9f" if primary else BORDER,
                     activeforeground=PANEL if primary else TEXT,
                     disabledforeground="#8290a2", relief="flat", bd=0,
                     font=("Segoe UI", 10, "bold"), padx=16, pady=10,
                     cursor="hand2", takefocus=True)


class MonitorApp:
    def __init__(self, root, history_dir=HISTORY_DIR):
        self.root = root
        self.history_dir = Path(history_dir)
        self.root.title("Pulse | Server Uptime Monitoring Log")
        width = min(1280, self.root.winfo_screenwidth() - 60)
        height = min(850, self.root.winfo_screenheight() - 60)
        self.root.geometry(f"{width}x{height}+20+10")
        self.root.minsize(min(1050, width), min(680, height))
        self.root.configure(bg=BG)
        self.report = None
        self.pending_report = None
        self.visible_entries = []
        self.timer = None
        self.running = False
        self.scenario = tk.StringVar(value="Stable Network")
        self.days = tk.StringVar(value="7")
        self.seed = tk.StringVar(value="")
        self.mode = tk.StringVar(value=MODES[1])
        self.previous_mode = None
        self.seed_enabled = tk.BooleanVar(value=False)
        self.reason = tk.StringVar(value="Start the recommended demo to see healthy readings, minor lag and a failure.")
        self.result_title = tk.StringVar(value="Ready for your first demo")
        self.detail = tk.StringVar(value="After starting, select any day to understand its result.")
        self.progress_text = tk.StringVar(value="Simulation only. Each row represents one day; no real server is contacted.")
        self.setup_styles()
        self.build_sidebar()
        self.build_dashboard()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=PANEL, background=BORDER,
                        foreground=TEXT, arrowcolor=TEXT, padding=8)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL), ("disabled", BG)],
                  foreground=[("readonly", TEXT), ("disabled", MUTED)],
                  selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", TEXT)])
        style.configure("TSpinbox", fieldbackground=PANEL, background=BORDER,
                        foreground=TEXT, arrowcolor=TEXT, padding=8)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=34, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"), padding=(12, 9), relief="flat")
        style.map("Treeview", background=[("selected", "#e3ecff")],
                  foreground=[("selected", TEXT)])
        style.configure("TScrollbar", background=BORDER, troughcolor=PANEL,
                        arrowcolor=MUTED, borderwidth=0)
        style.configure("Horizontal.TProgressbar", background=TEAL,
                        troughcolor=BORDER, borderwidth=0, thickness=4)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG, foreground=MUTED,
                        font=("Segoe UI", 10, "bold"), padding=(18, 10))
        style.map("TNotebook.Tab", background=[("selected", PANEL)],
                  foreground=[("selected", BLUE)])
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT,
                        font=("Segoe UI", 9))
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", BORDER)

    def build_sidebar(self):
        side = tk.Frame(self.root, bg=PANEL, width=280)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        inner = tk.Frame(side, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=20, pady=20)
        label(inner, "PULSE", 22, BLUE, True).pack(anchor="w")
        label(inner, "Server health simulator", 10, MUTED).pack(anchor="w", pady=(0, 18))
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x")

        label(inner, "1. Choose a run", 12, TEXT, True).pack(anchor="w", pady=(18, 8))
        self.mode_box = ttk.Combobox(inner, textvariable=self.mode, values=MODES,
                                    state="readonly", font=("Segoe UI", 10))
        self.mode_box.pack(fill="x")
        self.mode_box.bind("<<ComboboxSelected>>", self.update_setup)
        self.setup_hint = label(inner, "", 9, MUTED, justify="left", wraplength=234)
        self.setup_hint.pack(anchor="w", pady=(9, 18))

        label(inner, "2. Review the settings", 12, TEXT, True).pack(anchor="w", pady=(0, 12))
        label(inner, "Network condition", 10).pack(anchor="w", pady=(0, 6))
        self.scenario_box = ttk.Combobox(inner, textvariable=self.scenario,
                                        values=[v["name"] for v in SCENARIOS.values()],
                                        state="readonly", font=("Segoe UI", 10))
        self.scenario_box.pack(fill="x")
        self.scenario_box.bind("<<ComboboxSelected>>", self.update_setup)
        label(inner, "Number of simulated days", 10).pack(anchor="w", pady=(14, 6))
        self.day_box = ttk.Spinbox(inner, from_=1, to=365, textvariable=self.days,
                                  font=("Segoe UI", 10))
        self.day_box.pack(fill="x")
        self.settings_note = label(inner, "", 9, MUTED, justify="left", wraplength=234)
        self.settings_note.pack(anchor="w", pady=(7, 12))

        self.seed_options = tk.Frame(inner, bg=PANEL)
        self.seed_check = ttk.Checkbutton(self.seed_options, text="Repeat the same random run",
                                          variable=self.seed_enabled, command=self.toggle_seed)
        self.seed_check.pack(anchor="w")
        self.seed_fields = tk.Frame(self.seed_options, bg=PANEL)
        self.seed_box = tk.Entry(self.seed_fields, textvariable=self.seed, bg=PANEL, fg=TEXT,
                                 insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
                                 highlightthickness=1, highlightbackground=BORDER,
                                 highlightcolor=BLUE, disabledbackground=BG,
                                 disabledforeground=MUTED)
        self.seed_box.pack(fill="x", ipady=6)
        label(self.seed_fields, "Enter a whole number. The same number repeats the results.",
              9, MUTED, wraplength=234, justify="left").pack(anchor="w", pady=(5, 0))

        self.actions = tk.Frame(inner, bg=PANEL)
        self.actions.pack(fill="x", pady=(5, 0))
        self.run_button = button(self.actions, "Start demo", self.start_run, True)
        self.run_button.pack(fill="x")
        self.finish_button = button(self.actions, "Show all results now", self.finish_playback)
        self.finish_button.config(state="disabled")
        label(self.actions, "Results are saved automatically.", 9, MUTED).pack(anchor="w", pady=(9, 14))
        button(self.actions, "How does this work?", self.show_guide).pack(fill="x")
        self.update_setup()

    def card(self, parent):
        return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)

    def build_dashboard(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(side="left", fill="both", expand=True, padx=22, pady=18)
        self.body = body
        header = tk.Frame(body, bg=BG)
        header.pack(fill="x")
        self.export_button = button(header, "Save log...", self.export_log)
        self.export_button.pack(side="right", anchor="n", pady=4)
        button(header, "Saved runs", self.show_history).pack(side="right", anchor="n", padx=(0, 8), pady=4)
        self.export_button.config(state="disabled")
        label(header, "SERVER UPTIME MONITORING LOG", 9, MUTED, True).pack(anchor="w")
        label(header, "Server health, explained", 23, TEXT, True).pack(anchor="w", pady=(4, 4))
        label(header, "Pick a demo, press Start, and follow each day's result.",
              10, MUTED).pack(anchor="w")

        rules = tk.Frame(body, bg=BG)
        rules.pack(fill="x", pady=(15, 12))
        for index, (title, text, color) in enumerate([
            ("Healthy  /  0–100 ms", "Record the day and move on.", TEAL),
            ("Minor lag  /  101–300 ms", "Skip normal processing: continue.", AMBER),
            ("Failure  /  stop the loop", ">300 ms or 3 slow days in a row: break.", RED),
        ]):
            rules.columnconfigure(index, weight=1, uniform="rules")
            card = self.card(rules)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 4, 4 if index < 2 else 0))
            heading = label(card, title, 9, color, True, justify="left", wraplength=250)
            heading.pack(anchor="w", padx=12, pady=(10, 4))
            description = label(card, text, 9, MUTED, justify="left", wraplength=250)
            description.pack(anchor="w", padx=12, pady=(0, 10))
            card.bind("<Configure>", lambda event, h=heading, d=description:
                      (h.config(wraplength=max(100, event.width - 24)),
                       d.config(wraplength=max(100, event.width - 24))))

        stat_row = tk.Frame(body, bg=BG)
        stat_row.pack(fill="x", pady=(0, 12))
        self.stats = {}
        for i, (key, title, color) in enumerate([
            ("checked", "Days checked", BLUE), ("healthy", "Healthy", TEAL),
            ("lag", "Minor lag", AMBER), ("failure", "Failures", RED),
        ]):
            stat_row.columnconfigure(i, weight=1, uniform="stats")
            box = self.card(stat_row)
            box.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 4 if i < 3 else 0))
            label(box, title, 9, MUTED).pack(anchor="w", padx=13, pady=(9, 0))
            variable = tk.StringVar(value="0")
            self.stats[key] = variable
            label(box, size=22, color=color, bold=True, textvariable=variable).pack(anchor="w", padx=13, pady=(0, 8))

        self.notebook = ttk.Notebook(body)
        self.log_box = tk.Frame(self.notebook, bg=PANEL)
        self.charts = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(self.log_box, text="Daily results")
        self.notebook.add(self.charts, text="Charts & summary")
        self.charts_visible = False
        self.notebook.bind("<<NotebookTabChanged>>", lambda event: self.draw_charts())

        title_row = tk.Frame(self.log_box, bg=PANEL)
        title_row.pack(fill="x", padx=14, pady=(10, 7))
        label(title_row, "3. Read the daily results", 11, TEXT, True).pack(side="left")
        self.log_hint = label(title_row, "Start a demo to see the first result", 9, MUTED)
        self.log_hint.pack(side="right")
        self.detail_label = label(self.log_box, textvariable=self.detail, size=10,
                                  color=MUTED, wraplength=780, justify="left", anchor="w")
        self.detail_label.pack(side="bottom", fill="x", padx=14, pady=(10, 12))
        self.log_box.bind("<Configure>", lambda event:
                          self.detail_label.config(wraplength=max(200, event.width - 28)))
        table_frame = tk.Frame(self.log_box, bg=PANEL)
        table_frame.pack(fill="both", expand=True, padx=6, pady=(0, 3))
        self.table = ttk.Treeview(table_frame, columns=("day", "ping", "status", "streak", "action"),
                                  show="headings", height=7, selectmode="browse")
        for column, heading, width in [
            ("day", "Day", 68), ("ping", "Ping (ms)", 80), ("status", "Result", 185),
            ("streak", "Slow days in a row", 140), ("action", "Next step", 175),
        ]:
            self.table.heading(column, text=heading, anchor="w")
            self.table.column(column, width=width, minwidth=55, anchor="w",
                              stretch=column in ("status", "action"))
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.table.pack(side="left", fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.explain_selected_day)
        for status, color in COLORS.items():
            self.table.tag_configure(status, foreground=color)

        self.charts.columnconfigure(0, weight=3)
        self.charts.columnconfigure(1, weight=2)
        self.charts.rowconfigure(0, weight=1)
        chart_box = tk.Frame(self.charts, bg=PANEL)
        chart_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        label(chart_box, "Response time by day", 12, TEXT, True).pack(anchor="w", padx=17, pady=(16, 0))
        label(chart_box, "Ping in milliseconds (ms). Lower is faster.", 9, MUTED).pack(anchor="w", padx=17)
        self.timeline = tk.Canvas(chart_box, bg=PANEL, height=240, highlightthickness=0)
        self.timeline.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.timeline.bind("<Configure>", lambda event: self.draw_charts())
        dist_box = tk.Frame(self.charts, bg=PANEL)
        dist_box.grid(row=0, column=1, sticky="nsew")
        label(dist_box, "How the checks ended", 12, TEXT, True).pack(anchor="w", padx=17, pady=(16, 0))
        label(dist_box, "Counts include checked days only.", 9, MUTED).pack(anchor="w", padx=17)
        self.distribution = tk.Canvas(dist_box, bg=PANEL, height=240, highlightthickness=0)
        self.distribution.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.distribution.bind("<Configure>", lambda event: self.draw_charts())

        footer = tk.Frame(body, bg=BG)
        footer.pack(side="bottom", fill="x", pady=(7, 0))
        label(footer, textvariable=self.progress_text, size=9, color=MUTED,
              anchor="w").pack(fill="x")
        self.progress = ttk.Progressbar(body, mode="determinate")
        self.progress.pack(side="bottom", fill="x", pady=(8, 0))
        result_box = self.card(body)
        result_box.pack(side="bottom", fill="x", pady=(10, 0))
        self.result_heading = label(result_box, textvariable=self.result_title, size=11,
                                     color=BLUE, bold=True, anchor="w")
        self.result_heading.pack(fill="x", padx=13, pady=(9, 3))
        self.reason_label = label(result_box, textvariable=self.reason, size=10, color=MUTED,
                                  wraplength=780, justify="left", anchor="w")
        self.reason_label.pack(fill="x", padx=13, pady=(0, 10))
        result_box.bind("<Configure>", lambda event:
                        self.reason_label.config(wraplength=max(200, event.width - 26)))
        self.notebook.pack(fill="both", expand=True)

    def update_setup(self, event=None):
        demo = self.mode.get() != MODES[0]
        changed = self.mode.get() != self.previous_mode
        if demo:
            self.days.set("7")
            self.seed.set("")
            self.seed_enabled.set(False)
            self.scenario.set("Busy Network" if self.mode.get() == MODES[2] else "Unstable Network")
            self.seed_options.pack_forget()
        else:
            if changed:
                self.scenario.set("Stable Network")
                self.days.set("14")
            self.seed_options.pack(fill="x", before=self.actions, pady=(0, 12))
        self.previous_mode = self.mode.get()
        self.day_box.config(state="disabled" if demo else "normal")
        self.scenario_box.config(state="disabled" if demo else "readonly")
        self.seed_check.config(state="disabled" if demo else "normal")
        self.toggle_seed()
        self.run_button.config(text="Start demo" if demo else "Start simulation")
        key = next(k for k, v in SCENARIOS.items() if v["name"] == self.scenario.get())
        low, high = SCENARIOS[key]["range"]
        hint = f"Generate new readings from {low} to {high} ms. A smaller number means a faster response."
        if demo:
            hint = ("Recommended first try. Healthy days and minor lag lead to a failure on day 6."
                    if self.mode.get() == MODES[1] else
                    "See why 3 slow days in a row stop the checks on day 4.")
        self.setup_hint.config(text=hint)
        self.settings_note.config(text="Demo settings are filled in for you." if demo else
                                  "Choose 1–365 days. Each day is one simulated check.")

    def toggle_seed(self):
        enabled = self.seed_enabled.get() and self.mode.get() == MODES[0]
        if enabled:
            self.seed_fields.pack(fill="x", pady=(7, 0))
        else:
            self.seed_fields.pack_forget()
            self.seed.set("")
        self.seed_box.config(state="normal" if enabled and not self.running else "disabled")

    def toggle_charts(self):
        """Switch between the detailed log and optional charts."""
        self.charts_visible = self.notebook.select() != str(self.charts)
        self.notebook.select(self.charts if self.charts_visible else self.log_box)

    def show_guide(self):
        window = tk.Toplevel(self.root)
        window.title("Pulse | How the simulator works")
        window.configure(bg=PANEL)
        window.geometry("650x570")
        window.transient(self.root)
        label(window, "A quick guide", 21, TEXT, True).pack(anchor="w", padx=24, pady=(22, 10))
        sections = [
            ("What does ping mean?", "Ping is a response time in milliseconds (ms). Lower values are faster. Each row represents one simulated day."),
            ("Healthy: 0–100 ms", "The program records a healthy day and resets the count of slow days in a row."),
            ("Minor lag: 101–300 ms", "The response is slow. The continue statement skips healthy-day processing and moves to the next day."),
            ("When does it stop?", "A response above 300 ms, or 3 slow days in a row, triggers a failure. The break statement exits the loop."),
            ("What should I try first?", "Choose 'Demo: critical failure' and press Start demo. Select a result row to read its explanation. Try the repeated-lag demo next."),
        ]
        for title, explanation in sections:
            label(window, title, 11, BLUE, True).pack(anchor="w", padx=24, pady=(10, 3))
            label(window, explanation, 10, TEXT, wraplength=595,
                  justify="left").pack(anchor="w", padx=24)
        button(window, "Got it", window.destroy, True).pack(anchor="e", padx=24, pady=18)

    def add_result_row(self, entry):
        action = "Stop monitoring" if entry["action"] == "break" else "Check next day"
        if entry["action"] == "continue":
            action = "Skip to next day"
        item = self.table.insert("", "end", iid=str(entry["day"]),
                                 values=(f"Day {entry['day']}", entry["ping_ms"],
                                         FRIENDLY_STATUS[entry["status"]],
                                         f"{entry['lag_streak']} of 3", action),
                                 tags=(entry["status"],))
        self.table.see(item)
        self.table.selection_set(item)
        self.explain_day(entry)

    def explain_day(self, entry):
        prefix = f"Day {entry['day']}: {entry['ping_ms']} ms. "
        if entry["status"] == "HEALTHY":
            explanation = "The response is healthy (100 ms or less). Record this day and reset the slow-day count."
        elif entry["status"] == "MINOR LAG":
            explanation = (f"This is slow day {entry['lag_streak']} of 3 in a row. "
                           "The continue statement skips healthy processing and moves to the next day.")
        elif entry["status"] == "CRITICAL FAILURE":
            explanation = "The response is above 300 ms. The break statement stops the loop; later days are not checked."
        else:
            explanation = "This is the third slow day in a row. The break statement stops the loop before any later checks."
        self.detail.set(prefix + explanation)

    def explain_selected_day(self, event=None):
        selected = self.table.selection()
        if not selected:
            return
        day = int(selected[0])
        entry = next((entry for entry in self.visible_entries if entry["day"] == day), None)
        if entry:
            self.explain_day(entry)

    def start_run(self):
        if self.running:
            return
        try:
            try:
                days = int(self.days.get())
            except ValueError:
                raise ValueError("Enter a whole number of days, from 1 to 365.") from None
            if not 1 <= days <= 365:
                raise ValueError("Choose between 1 and 365 simulated days.")
            seed = None
            if self.seed_enabled.get() and self.mode.get() == MODES[0]:
                try:
                    seed = int(self.seed.get())
                except ValueError:
                    raise ValueError("Enter a whole number to repeat a run, or untick that option.") from None
            key = next(k for k, v in SCENARIOS.items() if v["name"] == self.scenario.get())
            readings = None
            if self.mode.get() != MODES[0]:
                if days > 7:
                    raise ValueError("Classroom demos support at most 7 days.")
                readings = DEMO_PINGS if self.mode.get() == MODES[1] else LAG_DEMO_PINGS
                seed = None
            self.pending_report = monitor_server(days, seed, readings, key)
        except (ValueError, StopIteration) as error:
            messagebox.showerror("Check simulation settings", str(error), parent=self.root)
            return
        self.report = None
        self.visible_entries = []
        self.table.delete(*self.table.get_children())
        self.notebook.select(self.log_box)
        self.progress.config(maximum=days, value=0)
        self.running = True
        self.run_button.config(state="disabled", text="Running...")
        self.finish_button.pack(fill="x", after=self.run_button, pady=(5, 0))
        self.finish_button.config(state="normal")
        self.export_button.config(state="disabled")
        self.seed_check.config(state="disabled")
        for widget in [self.mode_box, self.scenario_box, self.day_box, self.seed_box]:
            widget.config(state="disabled")
        self.log_hint.config(text=f"{days} planned days / select a row for help")
        self.result_title.set("Simulation running")
        self.result_heading.config(fg=BLUE)
        self.advance()

    def advance(self):
        self.timer = None
        index = len(self.visible_entries)
        if index >= len(self.pending_report["entries"]):
            self.complete_run()
            return
        entry = self.pending_report["entries"][index]
        self.visible_entries.append(entry)
        self.add_result_row(entry)
        self.refresh_results()
        self.reason.set(f"Checking day {entry['day']}: {FRIENDLY_STATUS[entry['status']].lower()}. Read the selected row's explanation above.")
        self.progress_text.set(f"Showing day {entry['day']} of {self.pending_report['requested_days']} planned days.")
        self.progress.config(value=entry["day"])
        self.timer = self.root.after(400, self.advance)

    def finish_playback(self):
        if not self.running:
            return
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        remaining = self.pending_report["entries"][len(self.visible_entries):]
        for entry in remaining:
            self.visible_entries.append(entry)
            self.add_result_row(entry)
        self.complete_run()

    def complete_run(self):
        self.running = False
        self.report = self.pending_report
        self.run_button.config(state="normal")
        self.finish_button.config(state="disabled")
        self.finish_button.pack_forget()
        self.export_button.config(state="normal")
        self.mode_box.config(state="readonly")
        self.update_setup()
        self.run_button.config(text="Run demo again" if self.mode.get() != MODES[0] else "Run again")
        self.refresh_results()
        self.progress.config(value=len(self.visible_entries))
        checked = len(self.visible_entries)
        remaining = self.report["requested_days"] - checked
        self.result_heading.config(fg=RED if self.report["critical_days"] else TEAL)
        if self.report["critical_days"]:
            self.result_title.set(f"Monitoring stopped on day {checked}")
        else:
            self.result_title.set(f"Finished: all {checked} days were checked")
        skipped = f" {remaining} planned day{'s were' if remaining != 1 else ' was'} not checked." if remaining else ""
        self.reason.set(self.report["stop_reason"] + skipped)
        self.log_hint.config(text=f"{checked} checked / {remaining} not checked")
        try:
            save_run_history(self.report, self.history_dir)
            self.progress_text.set("Saved automatically. Use Saved runs to compare results, or Save log... for a text file.")
        except OSError as error:
            self.progress_text.set("Run complete. Automatic saving failed; use Save log... to choose another folder.")
            messagebox.showwarning("History could not be saved", str(error), parent=self.root)

    def counts(self):
        return [sum(e["status"] == "HEALTHY" for e in self.visible_entries),
                sum(e["status"] == "MINOR LAG" for e in self.visible_entries),
                sum(e["action"] == "break" for e in self.visible_entries)]

    def refresh_results(self):
        healthy, lag, failure = self.counts()
        for key, value in zip(self.stats, [len(self.visible_entries), healthy, lag, failure]):
            self.stats[key].set(str(value))
        self.draw_charts()

    def draw_charts(self):
        if not hasattr(self, "distribution"):
            return
        canvas = self.timeline
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 80:
            return
        left, right, top, bottom = 42, w - 20, 20, h - 30
        maximum = max(400, max((e["ping_ms"] for e in self.visible_entries), default=0) + 40)

        def y(value):
            return bottom - value / maximum * (bottom - top)

        for value in [0, 100, 300]:
            color = BORDER if value == 0 else TEAL if value == 100 else RED
            canvas.create_line(left, y(value), right, y(value), fill=color, dash=(3, 5))
            canvas.create_text(left - 8, y(value), text=str(value), fill=MUTED,
                               anchor="e", font=("Segoe UI", 8))
        if not self.visible_entries:
            canvas.create_text((left + right) / 2, (top + bottom) / 2,
                               text="Run a demo to see response times", fill=MUTED,
                               font=("Segoe UI", 10))
        else:
            days = self.pending_report["requested_days"]
            points = [(left + (e["day"] - 1) / max(days - 1, 1) * (right - left),
                       y(e["ping_ms"])) for e in self.visible_entries]
            if len(points) > 1:
                canvas.create_line(*[coordinate for point in points for coordinate in point],
                                   fill=BLUE, width=2)
            for entry, (x, py) in zip(self.visible_entries, points):
                color = COLORS[entry["status"]]
                canvas.create_oval(x - 4, py - 4, x + 4, py + 4, fill=color, outline=PANEL, width=1)
            canvas.create_text(left, h - 10, text="Day 1", fill=MUTED, anchor="w", font=("Segoe UI", 8))
            canvas.create_text(right, h - 10, text=f"Day {days}", fill=MUTED, anchor="e", font=("Segoe UI", 8))

        canvas = self.distribution
        canvas.delete("all")
        width = canvas.winfo_width()
        counts = self.counts()
        total = sum(counts)
        rate = counts[0] / total * 100 if total else 0
        canvas.create_text(18, 22, text=f"{rate:.0f}%" if total else "—", fill=TEAL,
                           font=("Segoe UI", 22, "bold"), anchor="w")
        canvas.create_text(18, 46, text="of checked days were healthy" if total else "No checks yet",
                           fill=MUTED, font=("Segoe UI", 9), anchor="w")
        for i, (name, count, color) in enumerate(zip(["Healthy", "Minor lag", "Failure"], counts, [TEAL, AMBER, RED])):
            cy = 72 + i * 28
            canvas.create_text(18, cy, text=name, fill=TEXT, anchor="w", font=("Segoe UI", 9))
            canvas.create_text(width - 18, cy, text=str(count), fill=color, anchor="e", font=("Segoe UI", 9, "bold"))
            canvas.create_rectangle(18, cy + 12, max(19, width - 18), cy + 17, fill=BORDER, outline="")
            if count and total:
                canvas.create_rectangle(18, cy + 12, 18 + max(0, width - 36) * count / total,
                                        cy + 17, fill=color, outline="")

    def export_log(self):
        if self.report is None:
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Export simulation log",
                                            defaultextension=".txt", initialfile="server_health_log.txt",
                                            filetypes=[("Text log", "*.txt")])
        if path:
            try:
                Path(path).write_text(format_report(self.report) + "\n", encoding="utf-8")
                self.progress_text.set(f"Log exported to {path}")
            except OSError as error:
                messagebox.showerror("Could not export log", str(error), parent=self.root)

    def show_history(self):
        window = tk.Toplevel(self.root)
        window.title("Pulse | Saved runs")
        window.geometry("1000x650")
        window.configure(bg=BG)
        label(window, "Saved runs", 22, TEXT, True).pack(anchor="w", padx=22, pady=(20, 3))
        label(window, "Select a saved simulation to inspect its full report. Latest 100 runs shown.",
              10, MUTED).pack(anchor="w", padx=22, pady=(0, 14))
        table = ttk.Treeview(window, columns=("time", "scenario", "source", "checked", "result"),
                             show="headings", height=6)
        for name, title, width in [("time", "Saved at", 220), ("scenario", "Network", 150),
                                   ("source", "Readings", 110), ("checked", "Days checked", 100),
                                   ("result", "Outcome", 150)]:
            table.heading(name, text=title, anchor="w")
            table.column(name, width=width, anchor="w")
        table.pack(fill="x", padx=22)
        viewer = tk.Text(window, bg=PANEL, fg=TEXT, insertbackground=TEXT, wrap="none",
                         font=("Consolas", 10), relief="flat", padx=15, pady=12)
        viewer.pack(fill="both", expand=True, padx=22, pady=(14, 20))
        viewer.insert("1.0", "No saved runs yet. Run a simulation to create your first log.")
        viewer.config(state="disabled")
        records = {}
        try:
            paths = sorted(self.history_dir.glob("*.json"), reverse=True)[:100]
            for path in paths:
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                    report_text = format_report(record)
                    item = table.insert("", "end", values=(record["created_at"][:19].replace("T", " "),
                                        SCENARIOS[record["scenario"]]["name"], record["reading_source"],
                                        len(record["entries"]), "Stopped on failure" if record["critical_days"] else "Completed"))
                    records[item] = report_text
                except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
                    continue  # One damaged file must not prevent other runs from opening.
        except OSError as error:
            messagebox.showerror("Could not open history", str(error), parent=window)

        def select_run(event=None):
            selected = table.selection()
            if selected:
                viewer.config(state="normal")
                viewer.delete("1.0", "end")
                viewer.insert("1.0", records[selected[0]])
                viewer.config(state="disabled")

        table.bind("<<TreeviewSelect>>", select_run)
        if records:
            first = next(iter(records))
            table.selection_set(first)
            select_run()

    def close(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    MonitorApp(root)
    root.mainloop()
