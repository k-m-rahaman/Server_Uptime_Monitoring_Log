"""Tkinter desktop interface. All simulation decisions live in main.py."""

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from main import (DEMO_PINGS, LAG_DEMO_PINGS, SCENARIOS, comparison_rows,
                  export_csv, format_report, iter_monitor, report_statistics,
                  save_run_history, validate_settings)


BG = "#0a101b"
PANEL = "#111d2d"
RAISED = "#17263b"
BORDER = "#2a3c55"
TEXT = "#f1f5fb"
MUTED = "#a3b3c9"
TEAL = "#52e0b8"
AMBER = "#f4c36d"
RED = "#ff8596"
BLUE = "#87baff"
COLORS = {"HEALTHY": TEAL, "MINOR LAG": AMBER,
          "CRITICAL FAILURE": RED, "ESCALATED FAILURE": RED}
BASE_DIR = Path(__file__).resolve().parent
HISTORY_DIR = BASE_DIR / "logs" / "history"
MODES = ["Random scenario", "Critical failure demo", "Lag escalation demo"]


def label(parent, text="", size=10, color=TEXT, bold=False, **kwargs):
    return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                    font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)


def button(parent, text, command, primary=False):
    normal = TEAL if primary else RAISED
    hover = "#83ebcd" if primary else "#233a56"
    widget = tk.Button(parent, text=text, command=command,
                     bg=normal,
                     fg=BG if primary else TEXT,
                     activebackground=hover,
                     activeforeground=BG if primary else TEXT,
                     disabledforeground="#567086", relief="flat", bd=0,
                     highlightthickness=1, highlightbackground=TEAL if primary else BORDER,
                     highlightcolor=BLUE,
                     font=("Segoe UI", 10, "bold"), padx=16, pady=10,
                     cursor="hand2", takefocus=True)
    widget.bind("<Enter>", lambda event: widget.config(bg=hover)
                if str(widget["state"]) != "disabled" else None)
    widget.bind("<Leave>", lambda event: widget.config(bg=normal))
    return widget


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
        self.iterator = None
        self.step_mode_active = False
        self.teaching_mode = tk.BooleanVar(value=False)
        self.healthy_limit = tk.StringVar(value="100")
        self.critical_limit = tk.StringVar(value="300")
        self.lag_limit = tk.StringVar(value="3")
        self.rules_text = tk.StringVar()
        self.ping_metrics = tk.StringVar(value="Average: — ms  |  Highest: — ms")
        self.lag_metrics = tk.StringVar(value="Longest lag streak: — days")
        self.scenario = tk.StringVar(value="Stable Network")
        self.days = tk.StringVar(value="14")
        self.seed = tk.StringVar(value="")
        self.mode = tk.StringVar(value=MODES[0])
        self.reason = tk.StringVar(value="Ready to simulate. Choose a scenario or try a classroom demo.")
        self.progress_text = tk.StringVar(value="No simulation running")
        self.setup_styles()
        self.build_sidebar()
        self.build_dashboard()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=BG, background=BORDER,
                        foreground=TEXT, arrowcolor=MUTED, padding=8,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                        relief="flat", borderwidth=1)
        style.map("TCombobox", fieldbackground=[("readonly", BG), ("disabled", PANEL)],
                  foreground=[("readonly", TEXT), ("disabled", MUTED)],
                  selectbackground=[("readonly", BG)], selectforeground=[("readonly", TEXT)],
                  bordercolor=[("focus", TEAL)])
        style.configure("TSpinbox", fieldbackground=BG, background=BORDER,
                        foreground=TEXT, arrowcolor=MUTED, padding=8,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                        relief="flat", borderwidth=1)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=31, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"), padding=(12, 9), relief="flat",
                        bordercolor=BORDER, lightcolor=BG, darkcolor=BG)
        style.map("Treeview.Heading", background=[("active", RAISED)],
                  foreground=[("active", TEXT)])
        style.map("Treeview", background=[("selected", "#29435f")],
                  foreground=[("selected", TEXT)])
        style.configure("TScrollbar", background=BORDER, troughcolor=PANEL,
                        arrowcolor=MUTED, borderwidth=0)
        style.configure("Horizontal.TProgressbar", background=TEAL,
                        troughcolor=BORDER, borderwidth=0, thickness=4)
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT,
                        font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", PANEL)],
                  foreground=[("disabled", MUTED)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", BORDER)
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

    def build_sidebar(self):
        side = tk.Frame(self.root, bg=PANEL, width=264)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        inner = tk.Frame(side, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=20, pady=18)
        brand = tk.Frame(inner, bg=PANEL)
        brand.pack(fill="x")
        mark = tk.Canvas(brand, bg=PANEL, width=31, height=30, highlightthickness=0)
        mark.pack(side="left", padx=(0, 9))
        mark.create_line(2, 16, 8, 16, 11, 8, 16, 24, 20, 12, 24, 16, 29, 16,
                         fill=TEAL, width=2.4, capstyle="round", joinstyle="round")
        label(brand, "PULSE", 23, TEAL, True).pack(side="left")
        label(inner, "SERVER HEALTH LAB", 9, MUTED, True).pack(anchor="w", pady=(0, 16))
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x")
        setup_row = tk.Frame(inner, bg=PANEL)
        setup_row.pack(fill="x", pady=(16, 8))
        label(setup_row, "SIMULATION SETUP", 9, MUTED, True).pack(side="left")
        self.threshold_button = button(setup_row, "Thresholds...", self.show_thresholds)
        self.threshold_button.config(font=("Segoe UI", 8), padx=6, pady=3)
        self.threshold_button.pack(side="right")

        label(inner, "Network scenario", 10).pack(anchor="w", pady=(2, 6))
        self.scenario_box = ttk.Combobox(inner, textvariable=self.scenario,
                                        values=[v["name"] for v in SCENARIOS.values()],
                                        state="readonly", font=("Segoe UI", 10))
        self.scenario_box.pack(fill="x")
        self.scenario_box.bind("<<ComboboxSelected>>", self.update_setup)
        label(inner, "Simulated days  /  1–365", 10).pack(anchor="w", pady=(9, 6))
        self.day_box = ttk.Spinbox(inner, from_=1, to=365, textvariable=self.days,
                                   font=("Segoe UI", 10))
        self.day_box.pack(fill="x")
        label(inner, "Random seed  /  optional", 10).pack(anchor="w", pady=(9, 6))
        self.seed_box = tk.Entry(inner, textvariable=self.seed, bg=BG, fg=TEXT,
                                  insertbackground=TEXT, relief="flat",
                                  disabledbackground=PANEL, disabledforeground=MUTED,
                                  font=("Segoe UI", 11), highlightthickness=1,
                                  highlightbackground=BORDER, highlightcolor=TEAL)
        self.seed_box.pack(fill="x", ipady=8)
        label(inner, "Run mode", 10).pack(anchor="w", pady=(9, 6))
        self.mode_box = ttk.Combobox(inner, textvariable=self.mode, values=MODES,
                                    state="readonly", font=("Segoe UI", 10))
        self.mode_box.pack(fill="x")
        self.mode_box.bind("<<ComboboxSelected>>", self.update_setup)
        self.setup_hint = label(inner, "", 9, MUTED, justify="left", wraplength=214)
        self.setup_hint.pack(anchor="w", pady=(8, 8))
        self.teaching_check = ttk.Checkbutton(inner, text="Step-by-step teaching",
                                               variable=self.teaching_mode,
                                               command=self.toggle_teaching)
        self.teaching_check.pack(anchor="w", pady=(0, 9))
        self.run_button = button(inner, "Run simulation  >", self.start_run, True)
        self.run_button.pack(fill="x")
        self.playback_controls = tk.Frame(inner, bg=PANEL)
        self.playback_controls.pack(fill="x", pady=(4, 10))
        self.next_button = button(self.playback_controls, "Next Day >", self.next_day)
        self.next_button.config(font=("Segoe UI", 9, "bold"), padx=6, pady=9, state="disabled")
        self.finish_button = button(self.playback_controls, "Finish playback", self.finish_playback)
        self.finish_button.config(font=("Segoe UI", 9, "bold"), padx=6, pady=9)
        self.finish_button.pack(side="right", fill="x", expand=True)
        self.finish_button.config(state="disabled")
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x")
        label(inner, textvariable=self.rules_text, size=9, color=MUTED,
              wraplength=220, justify="left").pack(anchor="w", pady=(12, 0))
        self.update_setup()

    def card(self, parent):
        return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)

    def build_dashboard(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(side="left", fill="both", expand=True, padx=26, pady=18)
        header = tk.Frame(body, bg=BG)
        header.pack(fill="x")
        self.export_button = button(header, "Export log", self.export_log)
        self.export_button.pack(side="right", anchor="n", pady=7)
        self.csv_button = button(header, "Export CSV", self.export_csv_log)
        self.csv_button.pack(side="right", anchor="n", padx=(0, 8), pady=7)
        self.csv_button.config(state="disabled")
        button(header, "History", self.show_history).pack(side="right", anchor="n", padx=(0, 8), pady=7)
        self.export_button.config(state="disabled")
        label(header, "SERVER UPTIME MONITORING LOG", 9, TEAL, True).pack(anchor="w")
        label(header, "Server health overview", 25, TEXT, True).pack(anchor="w", pady=(4, 4))
        label(header, "Simulated daily checks. Clear signals. Explainable decisions.",
              10, MUTED).pack(anchor="w")

        stat_row = tk.Frame(body, bg=BG)
        stat_row.pack(fill="x", pady=(16, 14))
        self.stats = {}
        for i, (key, title, color) in enumerate([
            ("checked", "CHECKED DAYS", BLUE),
            ("healthy", "HEALTHY", TEAL),
            ("lag", "MINOR LAG", AMBER),
            ("failure", "FAILURES", RED),
        ]):
            stat_row.columnconfigure(i, weight=1, uniform="stats")
            box = self.card(stat_row)
            box.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 6 if i < 3 else 0))
            tk.Frame(box, bg=color, height=2).pack(fill="x")
            label(box, title, 9, MUTED, True).pack(anchor="w", padx=15, pady=(11, 2))
            variable = tk.StringVar(value="00")
            self.stats[key] = variable
            label(box, size=24, color=color, bold=True, textvariable=variable).pack(anchor="w", padx=15, pady=(0, 12))

        charts = tk.Frame(body, bg=BG)
        self.charts = charts
        charts.pack(fill="x")
        charts.columnconfigure(0, weight=3)
        charts.columnconfigure(1, weight=2)
        chart_box = self.card(charts)
        chart_box.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        label(chart_box, "PING RESPONSE", 10, TEXT, True).pack(anchor="w", padx=17, pady=(14, 0))
        label(chart_box, textvariable=self.ping_metrics, size=9, color=MUTED).pack(anchor="w", padx=17)
        self.timeline = tk.Canvas(chart_box, bg=PANEL, height=152, highlightthickness=0)
        self.timeline.pack(fill="x", padx=8, pady=(0, 6))
        self.timeline.bind("<Configure>", lambda event: self.draw_charts())
        dist_box = self.card(charts)
        dist_box.grid(row=0, column=1, sticky="nsew")
        self.dist_title = label(dist_box, "CHECK DISTRIBUTION", 10, TEXT, True)
        self.dist_title.pack(anchor="w", padx=17, pady=(14, 0))
        label(dist_box, textvariable=self.lag_metrics, size=9, color=MUTED).pack(anchor="w", padx=17)
        self.distribution = tk.Canvas(dist_box, bg=PANEL, height=152, highlightthickness=0)
        self.distribution.pack(fill="x", padx=8, pady=(0, 6))
        self.distribution.bind("<Configure>", lambda event: self.draw_charts())

        log_box = self.card(body)
        self.log_box = log_box
        self.charts_visible = True
        title_row = tk.Frame(log_box, bg=PANEL)
        title_row.pack(fill="x", padx=17, pady=(12, 10))
        label(title_row, "DAILY EVENT LOG", 10, TEXT, True).pack(side="left")
        self.expand_button = button(title_row, "Expand log", self.toggle_charts)
        self.expand_button.config(font=("Segoe UI", 9), padx=8, pady=2)
        self.expand_button.pack(side="right", padx=(10, 0))
        self.log_hint = label(title_row, "Waiting for a simulation", 9, MUTED)
        self.log_hint.pack(side="right")
        table_frame = tk.Frame(log_box, bg=PANEL)
        table_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.table = ttk.Treeview(table_frame, columns=("day", "ping", "status", "streak", "action"),
                                  show="headings", height=5, selectmode="browse")
        for column, heading, width in [("day", "DAY", 68), ("ping", "PING / ms", 90),
                                       ("status", "SERVER STATUS", 200),
                                       ("streak", "LAG STREAK", 95), ("action", "LOOP ACTION", 120)]:
            self.table.heading(column, text=heading, anchor="w")
            self.table.column(column, width=width, minwidth=60, anchor="w", stretch=column == "status")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.table.pack(side="left", fill="both", expand=True)
        for status, color in COLORS.items():
            tint = ("#142c29" if status == "HEALTHY" else
                    "#2c281e" if status == "MINOR LAG" else "#342130")
            self.table.tag_configure(status, foreground=color, background=tint)

        self.reason_label = label(body, textvariable=self.reason, size=10, color=MUTED,
                                  wraplength=800, justify="left", anchor="w")
        body.bind("<Configure>", lambda event: self.reason_label.config(wraplength=max(200, event.width - 8)))
        self.progress = ttk.Progressbar(body, mode="determinate")
        footer = tk.Frame(body, bg=BG)
        footer.pack(side="bottom", fill="x", pady=(8, 0))
        label(footer, textvariable=self.progress_text, size=9, color=MUTED).pack(side="left")
        label(footer, "SIMULATION ONLY  /  NO NETWORK TRAFFIC", 8, MUTED).pack(side="right")
        self.progress.pack(side="bottom", fill="x")
        self.reason_label.pack(side="bottom", fill="x", pady=(0, 10))
        log_box.pack(fill="both", expand=True, pady=(14, 12))

    def update_setup(self, event=None):
        demo = self.mode.get() != MODES[0]
        if demo:
            self.days.set("7")
            self.seed.set("")
            self.scenario.set("Busy Network" if self.mode.get() == MODES[2] else "Unstable Network")
        self.day_box.config(state="disabled" if demo else "normal")
        self.seed_box.config(state="disabled" if demo else "normal")
        self.scenario_box.config(state="disabled" if demo else "readonly")
        key = next(k for k, v in SCENARIOS.items() if v["name"] == self.scenario.get())
        low, high = SCENARIOS[key]["range"]
        hint = f"Random readings: {low}–{high} ms. Each iteration represents one day."
        limits = self.current_limits()
        self.rules_text.set(
            f"Healthy: 0–{limits['healthy_limit']} ms\n"
            f"Lag: {limits['healthy_limit'] + 1}–{limits['critical_limit']} ms\n"
            f"Stop: >{limits['critical_limit']} ms or {limits['lag_limit']} lag spikes in a row"
        )
        if demo:
            defaults = tuple(limits.values()) == (100, 300, 3)
            if defaults:
                hint = ("Fixed readings show an immediate critical failure on day 6."
                        if self.mode.get() == MODES[1] else
                        "Fixed readings show 3 consecutive lag spikes and escalation on day 4.")
            else:
                hint = "Fixed demo readings use your custom thresholds; the stopping day may change."
        self.setup_hint.config(text=hint)

    def current_limits(self):
        try:
            return {"healthy_limit": int(self.healthy_limit.get()),
                    "critical_limit": int(self.critical_limit.get()),
                    "lag_limit": int(self.lag_limit.get())}
        except ValueError:
            raise ValueError("All thresholds must be whole numbers.") from None

    def apply_thresholds(self, healthy, critical, lag):
        values = [int(value) if isinstance(value, str) else value
                  for value in (healthy, critical, lag)]
        validate_settings(1, "stable", *values)
        if self.running:
            raise ValueError("Finish the current simulation before changing thresholds.")
        for variable, value in zip((self.healthy_limit, self.critical_limit, self.lag_limit), values):
            variable.set(str(value))
        self.update_setup()

    def show_thresholds(self):
        if self.running:
            return
        window = tk.Toplevel(self.root)
        window.title("Pulse | Simulation thresholds")
        window.geometry("480x430")
        window.configure(bg=BG)
        window.transient(self.root)
        label(window, "Simulation thresholds", 20, TEXT, True).pack(anchor="w", padx=22, pady=(20, 6))
        label(window, "These rules apply to your next run, including fixed demos.",
              10, MUTED, wraplength=430, justify="left").pack(anchor="w", padx=22, pady=(0, 14))
        fields = []
        for title, value in [("Healthy limit (ms)", self.healthy_limit.get()),
                             ("Critical limit (ms)", self.critical_limit.get()),
                             ("Consecutive lag limit (days)", self.lag_limit.get())]:
            row = tk.Frame(window, bg=BG)
            row.pack(fill="x", padx=22, pady=7)
            label(row, title, 10).pack(side="left")
            variable = tk.StringVar(value=value)
            fields.append(variable)
            ttk.Spinbox(row, from_=0, to=10000, textvariable=variable,
                        width=9, font=("Segoe UI", 10)).pack(side="right")
        label(window, "Use 0 ≤ healthy < critical, and a lag limit of at least 1.",
              9, MUTED, wraplength=430, justify="left").pack(anchor="w", padx=22, pady=(14, 10))
        actions = tk.Frame(window, bg=BG)
        actions.pack(fill="x", padx=22, pady=12)

        def reset():
            for variable, value in zip(fields, ("100", "300", "3")):
                variable.set(value)

        def apply():
            try:
                self.apply_thresholds(*(variable.get() for variable in fields))
            except ValueError as error:
                messagebox.showerror("Check the thresholds", str(error), parent=window)
                return
            window.destroy()

        button(actions, "Reset defaults", reset).pack(side="left")
        button(actions, "Apply settings", apply, True).pack(side="right")

    def toggle_teaching(self):
        if self.running:
            return
        self.step_mode_active = self.teaching_mode.get()
        if self.step_mode_active:
            self.next_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
        else:
            self.next_button.pack_forget()
        if hasattr(self, "dist_title"):
            self.dist_title.config(text="PYTHON TEACHING" if self.step_mode_active else "CHECK DISTRIBUTION")
            self.draw_charts()

    def next_day(self):
        if self.running and self.step_mode_active:
            self.advance()

    def toggle_charts(self):
        self.charts_visible = not self.charts_visible
        if self.charts_visible:
            self.charts.pack(fill="x", before=self.log_box)
            self.expand_button.config(text="Expand log")
        else:
            self.charts.pack_forget()
            self.expand_button.config(text="Show charts")

    def start_run(self):
        if self.running:
            return
        try:
            days = int(self.days.get())
            if not 1 <= days <= 365:
                raise ValueError("Choose between 1 and 365 simulated days.")
            seed = int(self.seed.get()) if self.seed.get().strip() else None
            key = next(k for k, v in SCENARIOS.items() if v["name"] == self.scenario.get())
            readings = None
            if self.mode.get() != MODES[0]:
                if days > 7:
                    raise ValueError("Classroom demos support at most 7 days.")
                readings = DEMO_PINGS if self.mode.get() == MODES[1] else LAG_DEMO_PINGS
                seed = None
            limits = self.current_limits()
            validate_settings(days, key, **limits)
            self.iterator = iter_monitor(days, seed, readings, key, **limits)
        except (ValueError, StopIteration) as error:
            messagebox.showerror("Check simulation settings", str(error), parent=self.root)
            return
        self.report = None
        self.visible_entries = []
        self.pending_report = {"requested_days": days, "scenario": key,
                               "seed": seed, "entries": [], **limits}
        self.table.delete(*self.table.get_children())
        self.progress.config(maximum=days, value=0)
        self.running = True
        self.step_mode_active = self.teaching_mode.get()
        self.run_button.config(state="disabled")
        self.finish_button.config(state="normal")
        self.export_button.config(state="disabled")
        self.csv_button.config(state="disabled")
        self.threshold_button.config(state="disabled")
        self.teaching_check.config(state="disabled")
        for widget in [self.mode_box, self.scenario_box, self.day_box, self.seed_box]:
            widget.config(state="disabled")
        self.log_hint.config(text=f"{SCENARIOS[key]['name']}  /  {self.mode.get()}")
        self.reason_label.config(fg=MUTED)
        self.refresh_results()
        if self.step_mode_active:
            self.next_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
            self.next_button.config(state="normal")
            self.dist_title.config(text="PYTHON TEACHING")
            self.reason.set("Teaching mode paused. Click Next Day to execute the first check.")
            self.progress_text.set(f"0 of {days} days checked / one real Python iteration per press")
        else:
            self.next_button.pack_forget()
            self.dist_title.config(text="CHECK DISTRIBUTION")
            self.advance()

    def append_entry(self, entry):
        self.visible_entries.append(entry)
        self.pending_report["entries"] = list(self.visible_entries)
        limit = self.pending_report["lag_limit"]
        item = self.table.insert("", "end", values=(f"{entry['day']:03d}", entry["ping_ms"],
                                 entry["status"], f"{entry['lag_streak']} / {limit}", entry["action"]),
                                 tags=(entry["status"],))
        self.table.see(item)
        self.refresh_results()
        if self.step_mode_active:
            self.reason.set(f"Day {entry['day']}: {entry['explanation']}")
        else:
            self.reason.set(f"Day {entry['day']}: {entry['status'].lower()} / loop action: {entry['action']}")
        self.progress_text.set(f"{entry['day']} of {self.pending_report['requested_days']} planned days checked")
        self.progress.config(value=entry["day"])

    def advance(self):
        self.timer = None
        if not self.running or self.iterator is None:
            return
        try:
            entry = next(self.iterator)
        except StopIteration as finished:
            self.pending_report = finished.value
            self.complete_run()
            return
        self.append_entry(entry)
        terminal = entry["action"] == "break" or entry["day"] == self.pending_report["requested_days"]
        if terminal:
            # Resume only to execute generator cleanup and receive its final report.
            try:
                next(self.iterator)
            except StopIteration as finished:
                self.pending_report = finished.value
                self.complete_run()
            return
        if not self.step_mode_active:
            self.timer = self.root.after(260, self.advance)

    def finish_playback(self):
        if not self.running:
            return
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        while True:
            try:
                self.append_entry(next(self.iterator))
            except StopIteration as finished:
                self.pending_report = finished.value
                break
        self.complete_run()

    def complete_run(self):
        self.running = False
        self.iterator = None
        self.report = {**self.pending_report,
                       "presentation_mode": "step-by-step" if self.step_mode_active else "automatic"}
        self.pending_report = self.report
        self.run_button.config(state="normal")
        self.finish_button.config(state="disabled")
        self.next_button.config(state="disabled")
        self.export_button.config(state="normal")
        self.csv_button.config(state="normal")
        self.threshold_button.config(state="normal")
        self.teaching_check.config(state="normal")
        self.mode_box.config(state="readonly")
        self.update_setup()
        self.refresh_results()
        self.progress.config(value=len(self.visible_entries))
        color = RED if self.report["critical_days"] else TEAL
        self.reason_label.config(fg=color)
        explanation = self.report["stop_reason"]
        if self.step_mode_active and self.visible_entries:
            explanation += f" Python action: {self.visible_entries[-1]['highlight']}."
        self.reason.set(explanation)
        remaining = self.report["requested_days"] - len(self.visible_entries)
        try:
            save_run_history(self.report, self.history_dir)
            self.progress_text.set(f"Run saved / {remaining} days not evaluated / History can compare two runs")
        except OSError as error:
            self.progress_text.set("Run complete; history could not be saved. Use Export log to save elsewhere.")
            messagebox.showwarning("History could not be saved", str(error), parent=self.root)

    def counts(self):
        return [sum(e["status"] == "HEALTHY" for e in self.visible_entries),
                sum(e["status"] == "MINOR LAG" for e in self.visible_entries),
                sum(e["action"] == "break" for e in self.visible_entries)]

    def refresh_results(self):
        healthy, lag, failure = self.counts()
        for key, value in zip(self.stats, [len(self.visible_entries), healthy, lag, failure]):
            self.stats[key].set(f"{value:02d}")
        statistics = report_statistics({"entries": self.visible_entries})
        if statistics["checked_days"]:
            self.ping_metrics.set(f"Average: {statistics['average_ping_ms']:.1f} ms  |  Highest: {statistics['highest_ping_ms']} ms")
            self.lag_metrics.set(f"Longest lag streak: {statistics['max_lag_streak']} days")
        else:
            self.ping_metrics.set("Average: — ms  |  Highest: — ms")
            self.lag_metrics.set("Longest lag streak: — days")
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
        limits = self.pending_report if self.pending_report is not None else self.current_limits()
        healthy_limit = limits["healthy_limit"]
        critical_limit = limits["critical_limit"]
        maximum = max(400, critical_limit + 100,
                      max((e["ping_ms"] for e in self.visible_entries), default=0) + 40)

        def y(value):
            return bottom - value / maximum * (bottom - top)

        # Faint bands show the existing health thresholds behind the readings.
        canvas.create_rectangle(left, top, right, y(critical_limit), fill="#251d2c", outline="")
        canvas.create_rectangle(left, y(critical_limit), right, y(healthy_limit), fill="#24251f", outline="")
        canvas.create_rectangle(left, y(healthy_limit), right, bottom, fill="#102b29", outline="")
        for fraction in [0, 0.25, 0.5, 0.75, 1]:
            x = left + fraction * (right - left)
            canvas.create_line(x, top, x, bottom, fill="#263247", dash=(2, 6))

        points = []
        if self.visible_entries:
            days = self.pending_report["requested_days"]
            points = [(left + (e["day"] - 1) / max(days - 1, 1) * (right - left),
                       y(e["ping_ms"])) for e in self.visible_entries]
            last = self.visible_entries[-1]
            if last["action"] == "break" and last["day"] < days:
                stop_x = points[-1][0]
                canvas.create_rectangle(stop_x, top, right, bottom, fill="#0d1725", outline="")
                if right - stop_x > 85:
                    canvas.create_text((stop_x + right) / 2, top + 12, text="Not checked",
                                       fill=MUTED, font=("Segoe UI", 8))

        for value in sorted({0, healthy_limit, critical_limit, maximum}):
            if value > maximum:
                continue
            color = "#357e70" if value == healthy_limit else "#925166" if value == critical_limit else BORDER
            canvas.create_line(left, y(value), right, y(value), fill=color, dash=(3, 5))
            canvas.create_text(left - 8, y(value), text=str(value), fill=MUTED,
                               anchor="e", font=("Segoe UI", 8))

        if not points:
            canvas.create_text((left + right) / 2, (top + bottom) / 2,
                               text="Your ping timeline will appear here", fill=MUTED,
                               font=("Segoe UI", 10))
        else:
            if len(points) > 1:
                area = [(points[0][0], bottom), *points, (points[-1][0], bottom)]
                canvas.create_polygon(*[coordinate for point in area for coordinate in point],
                                      fill="#172e47", outline="")
                canvas.create_line(*[coordinate for point in points for coordinate in point],
                                   fill=BLUE, width=2.2, joinstyle="round")
            for entry, (x, py) in zip(self.visible_entries, points):
                color = COLORS[entry["status"]]
                canvas.create_oval(x - 5, py - 5, x + 5, py + 5,
                                   fill=PANEL, outline=color, width=1.5)
                canvas.create_oval(x - 2, py - 2, x + 2, py + 2,
                                   fill=color, outline="")
            last = self.visible_entries[-1]
            last_x, last_y = points[-1]
            if last["action"] == "break":
                canvas.create_line(last_x, top, last_x, bottom, fill=RED, dash=(3, 4))
            canvas.create_text(min(right - 12, max(left + 16, last_x)),
                               max(top + 7, last_y - 15), text=f"{last['ping_ms']} ms",
                               fill=COLORS[last["status"]], font=("Segoe UI", 9, "bold"))
            canvas.create_text(left, h - 10, text="Day 1", fill=MUTED,
                               anchor="w", font=("Segoe UI", 8))
            canvas.create_text(right, h - 10, text=f"Day {days}", fill=MUTED,
                               anchor="e", font=("Segoe UI", 8))

        canvas = self.distribution
        canvas.delete("all")
        width = canvas.winfo_width()
        if self.step_mode_active:
            current = self.visible_entries[-1]["highlight"] if self.visible_entries else None
            self.highlighted_action = current
            message = ("Click Next Day for one check" if self.running else
                       "Last executed Python action" if self.visible_entries else "Run simulation, then Next Day")
            canvas.create_text(16, 15, text=message, fill=MUTED,
                               anchor="w", font=("Segoe UI", 9))
            for index, (keyword, caption, color) in enumerate([
                ("for", "check each simulated day", BLUE),
                ("continue", "skip healthy processing", AMBER),
                ("break", "stop all later checks", RED),
            ]):
                cy = 47 + index * 34
                active = current == keyword
                canvas.create_rectangle(12, cy - 13, max(13, width - 12), cy + 14,
                                        fill=RAISED if active else PANEL,
                                        outline=color if active else BORDER)
                canvas.create_text(22, cy, text=keyword, anchor="w",
                                   fill=color if active else MUTED,
                                   font=("Consolas", 11, "bold"))
                canvas.create_text(107, cy, text=caption, anchor="w",
                                   fill=TEXT if active else MUTED, font=("Segoe UI", 8))
            return
        self.highlighted_action = None
        counts = self.counts()
        total = sum(counts)
        rate = counts[0] / total * 100 if total else 0
        canvas.create_text(18, 22, text=f"{rate:.0f}%" if total else "—", fill=TEAL,
                           font=("Segoe UI", 22, "bold"), anchor="w")
        canvas.create_text(18, 46, text="healthy check rate" if total else "No checks yet",
                           fill=MUTED, font=("Segoe UI", 9), anchor="w")
        for i, (name, count, color) in enumerate(zip(["Healthy", "Minor lag", "Failure"],
                                                    counts, [TEAL, AMBER, RED])):
            cy = 72 + i * 28
            canvas.create_text(18, cy, text=name, fill=TEXT, anchor="w", font=("Segoe UI", 9))
            canvas.create_text(width - 18, cy, text=str(count), fill=color,
                               anchor="e", font=("Segoe UI", 9, "bold"))
            canvas.create_line(20, cy + 15, max(21, width - 20), cy + 15,
                               fill=BORDER, width=5, capstyle="round")
            if count and total:
                canvas.create_line(20, cy + 15, 20 + max(1, width - 40) * count / total,
                                   cy + 15, fill=color, width=5, capstyle="round")

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

    def export_csv_log(self):
        if self.report is None:
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Export daily readings as CSV",
                                            defaultextension=".csv", initialfile="server_health_readings.csv",
                                            filetypes=[("CSV spreadsheet", "*.csv")])
        if path:
            try:
                export_csv(self.report, path)
                self.progress_text.set(f"CSV exported: {path}")
            except OSError as error:
                messagebox.showerror("Could not export CSV", str(error), parent=self.root)

    def load_history_records(self):
        records = []
        for path in sorted(self.history_dir.glob("*.json"), reverse=True)[:100]:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(record, dict) or not isinstance(record.get("entries"), list):
                    continue
                entries = record["entries"]
                if not entries or any(not isinstance(entry, dict) or
                                      entry.get("status") not in COLORS for entry in entries):
                    continue
                for entry in entries:
                    if (type(entry.get("day")) is not int or entry["day"] < 1 or
                            type(entry.get("ping_ms")) is not int or entry["ping_ms"] < 0):
                        raise ValueError("Invalid saved reading")
                record.setdefault("scenario", "stable")
                record.setdefault("requested_days", len(entries))
                validate_settings(record["requested_days"], record["scenario"],
                                  record.get("healthy_limit", 100),
                                  record.get("critical_limit", 300), record.get("lag_limit", 3))
                if record["requested_days"] < len(entries):
                    continue
                record["healthy_days"] = sum(e["status"] == "HEALTHY" for e in entries)
                record["lag_days"] = sum(e["status"] == "MINOR LAG" for e in entries)
                record["critical_days"] = sum(e["status"] in ("CRITICAL FAILURE", "ESCALATED FAILURE")
                                               for e in entries)
                record.setdefault("reading_source", "random")
                record["created_at"] = str(record.get("created_at", path.stem))
                format_report(record)  # Accept legacy fields; reject incomplete records.
                records.append(record)
            except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
                continue
        return records

    def show_history(self):
        window = tk.Toplevel(self.root)
        window.title("Pulse | Run history")
        window.geometry("1000x650")
        window.configure(bg=BG)
        label(window, "Run history", 22, TEXT, True).pack(anchor="w", padx=22, pady=(20, 3))
        actions = tk.Frame(window, bg=BG)
        actions.pack(fill="x", padx=22, pady=(0, 12))
        label(actions, "Select one run to inspect; Ctrl+click two runs to compare.",
              10, MUTED).pack(side="left")
        compare_button = button(actions, "Compare selected (0/2)", lambda: compare_selected())
        compare_button.pack(side="right")
        compare_button.config(state="disabled")
        table_frame = tk.Frame(window, bg=PANEL)
        table_frame.pack(fill="x", padx=22)
        table = ttk.Treeview(table_frame, columns=("time", "scenario", "source", "checked", "result"),
                             show="headings", height=5, selectmode="extended")
        for name, title, width in [("time", "SAVED AT", 220), ("scenario", "SCENARIO", 150),
                                   ("source", "READINGS", 110), ("checked", "CHECKED", 80),
                                   ("result", "RESULT", 150)]:
            table.heading(name, text=title, anchor="w")
            table.column(name, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        table.pack(side="left", fill="x", expand=True)
        viewer = tk.Text(window, bg=PANEL, fg=TEXT, insertbackground=TEXT, wrap="word",
                         font=("Consolas", 10), relief="flat", padx=15, pady=12)
        viewer.pack(fill="both", expand=True, padx=22, pady=(14, 20))
        viewer.insert("1.0", "No saved runs yet. Complete a simulation to create your first log.")
        viewer.config(state="disabled")
        records = {}
        self.history_table = table
        self.history_compare_button = compare_button
        try:
            for record in self.load_history_records():
                item = table.insert("", "end", values=(record["created_at"][:19].replace("T", " "),
                                    SCENARIOS[record["scenario"]]["name"], record["reading_source"],
                                    len(record["entries"]),
                                    "Stopped on failure" if record["critical_days"] else "Completed"))
                records[item] = record
        except OSError as error:
            messagebox.showerror("Could not open history", str(error), parent=window)

        def select_run(event=None):
            selected = table.selection()
            compare_button.config(state="normal" if len(selected) == 2 else "disabled",
                                  text=f"Compare selected ({len(selected)}/2)")
            if selected:
                viewer.config(state="normal")
                viewer.delete("1.0", "end")
                viewer.insert("1.0", format_report(records[selected[0]]))
                viewer.config(state="disabled")

        def compare_selected():
            selected = table.selection()
            if len(selected) == 2:
                self.show_comparison(records[selected[0]], records[selected[1]])

        table.bind("<<TreeviewSelect>>", select_run)
        if records:
            table.selection_set(next(iter(records)))
            select_run()
        return window

    def show_comparison(self, first, second):
        window = tk.Toplevel(self.root)
        window.title("Pulse | Compare two runs")
        window.geometry("1040x660")
        window.minsize(850, 540)
        window.configure(bg=BG)
        label(window, "Compare two saved runs", 21, TEXT, True).pack(anchor="w", padx=22, pady=(18, 3))
        label(window, "Compare settings, checked-day statistics and stopping reasons.",
              10, MUTED).pack(anchor="w", padx=22, pady=(0, 12))
        identifiers = tk.Frame(window, bg=BG)
        identifiers.pack(fill="x", padx=22, pady=(0, 8))
        for side, report in [("Run A", first), ("Run B", second)]:
            text = f"{side}: {report.get('created_at', report.get('run_id', 'selected run'))}"
            label(identifiers, text, 9, BLUE if side == "Run A" else TEAL).pack(
                side="left" if side == "Run A" else "right")
        table_frame = tk.Frame(window, bg=PANEL)
        table_frame.pack(fill="both", expand=True, padx=22)
        table = ttk.Treeview(table_frame, columns=("metric", "a", "b"), show="headings", height=13)
        for column, title, width in [("metric", "METRIC", 200), ("a", "RUN A", 350), ("b", "RUN B", 350)]:
            table.heading(column, text=title, anchor="w")
            table.column(column, width=width, minwidth=100, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        table.pack(fill="both", expand=True)
        for row in comparison_rows(first, second):
            table.insert("", "end", values=row)
        window.comparison_table = table
        reasons = tk.Frame(window, bg=BG)
        reasons.pack(fill="x", padx=22, pady=(12, 16))
        reasons.columnconfigure(0, weight=1, uniform="reasons")
        reasons.columnconfigure(1, weight=1, uniform="reasons")
        for column, (title, report, color) in enumerate([("A", first, BLUE), ("B", second, TEAL)]):
            box = self.card(reasons)
            box.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 5, 5 if column == 0 else 0))
            label(box, f"Run {title}: {report.get('stop_reason', 'Completed')}", 9, color,
                  wraplength=455, justify="left").pack(anchor="w", padx=12, pady=10)
        return window

    def close(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    MonitorApp(root)
    root.mainloop()
