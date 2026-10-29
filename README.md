# Pulse — Server Uptime Monitoring Log

**Python Project | Semester 3 | Section J | Group 1**

A Python mini project that simulates daily server health using **for loops, random numbers, continue and break**. It includes a dark desktop dashboard, a step-by-step teaching mode and a terminal interface. Both interfaces use the same Python simulation.

## Group members

| No. | Member |
| --- | --- |
| 1 | Kazi Mustafijur Rhaman |
| 2 | Anisha Akhtar |
| 3 | Koyel Basu |
| 4 | Suraiya Yeasmin |

## Submission documentation

The four-page project report includes the abstract, objectives, algorithm flowchart, graphical demo results, validation, conclusion and future scope.

- [PDF report for printing and submission](docs/PROJECT_DOCUMENTATION.pdf)
- [Editable Word report](docs/PROJECT_DOCUMENTATION.docx)

## Objective

Generate simulated daily ping readings, use continue to bypass healthy-day processing after minor lag, and use break to stop monitoring when a failure rule is met. The output is a daily log with a clear explanation of server health and the exact reason monitoring stopped.

## Quick start

Requirements: **Python 3.10 or later with Tkinter**. The project uses the Python standard library; no pip packages are needed.

On Windows, open the extracted project folder and double-click **run_gui.bat**. Or open a terminal in that folder and run:

    python gui.py

The Windows launcher tries py, python and an available Codex Python runtime. Tkinter is normally included with the official Windows Python installer. On Linux, install your distribution's Tkinter package if necessary. Check Tkinter availability with:

    python -m tkinter

A display of 1280 × 800 or larger is recommended. **Expand log** gives the daily table more space.

### Run in VS Code

1. Select **File → Open Folder** and open this project folder, the one containing gui.py and main.py.
2. Select **Terminal → New Terminal**.
3. In a Windows PowerShell terminal, run:

       .\run_gui.bat

4. The dashboard opens in its own window. After editing code, save it, close the dashboard and launch it again.

## What the project includes

| Feature | Purpose |
| --- | --- |
| Network scenarios | Generate readings for stable, busy or unstable conditions. |
| Fixed demonstrations | Reliably demonstrate critical failure and repeated-lag escalation. |
| Step-by-step teaching | Advance one day at a time and highlight for, continue or break. |
| Adjustable thresholds | Explore how different health and failure rules change the result. |
| Live charts and daily log | Follow readings, statuses, lag streaks and loop actions. |
| Run statistics | Show average ping, highest ping, longest lag streak and healthy-check rate. |
| Saved history and comparison | Inspect past runs and compare two results side by side. |
| Text and CSV export | Save a readable report or spreadsheet-ready daily records. |

The dashboard retains its dark layout, scenario controls, summary cards, charts and colour-coded event table.

## Use the dashboard

### 1. Try the standard demonstrations

Select **Critical failure demo** under Run mode and click **Run simulation**. With default thresholds, monitoring stops on day 6 at 301 ms. Day 7 is never checked.

Next select **Lag escalation demo**. With the defaults, days 2 and 3 continue after minor lag, and the third consecutive lag reading stops monitoring on day 4.

Choose **Random scenario** to generate new readings. Set the network and number of days. The dashboard initially uses 14 days for random mode; fixed demos plan seven days. The GUI supports 1–365 simulated days.

The **Random seed** field is optional. Leave it blank for new random readings. Enter a number such as 42 to repeat the same run with the same scenario, days and thresholds.

### 2. Learn one day at a time

Enable **Step-by-step teaching**, start a run and use **Next Day** to advance through its checks. The teaching pane highlights the relevant Python control-flow statement and explains the current decision.

- A healthy day follows normal processing.
- An ordinary lag day highlights continue.
- A critical or escalated failure highlights break and ends the run.

The teaching mode executes the shared Python generator lazily. Later readings are not generated or consumed before the run advances, and no reading is processed after failure.

**Finish playback** completes the remaining checks immediately, following the same stopping rules.

### 3. Change the rules

Open **Thresholds...** to set:

| Setting | Default | Meaning |
| --- | --- | --- |
| Healthy limit | 100 ms | Readings at or below this limit are healthy. |
| Critical limit | 300 ms | Readings above this limit fail immediately. |
| Consecutive-lag limit | 3 days | This many lag readings in a row trigger escalation. |

Limits must be whole numbers, with **0 ≤ healthy limit < critical limit**, and the consecutive-lag limit must be at least 1. Use **Reset defaults** to return to 100 ms, 300 ms and 3 days.

Changed thresholds also apply to the fixed demos, so their stopping day can change. Each saved run records the thresholds used.

### 4. Read the statistics

Average ping, highest ping and longest lag streak describe **checked days only**. Days skipped after failure never enter these calculations.

**Healthy check rate = healthy days ÷ checked days × 100.**

A terminal failure day belongs to the failure category, including a lag reading that reaches the escalation limit. Thus healthy + minor lag + failure equals the number of checked days.

### 5. Compare and export

Open **History** to inspect completed runs. To compare results, select exactly two rows using **Ctrl+click**, then click **Compare**. The comparison shows their settings, counts, statistics and stop reasons side by side. Earlier saved runs remain readable and use the original default thresholds when those fields are absent.

- **Export log** saves a readable text report.
- **Export CSV** saves processed daily rows, including the thresholds used.
- **Expand log** temporarily hides charts to show more table rows.

See [an example CSV export](examples/demo_readings.csv) for the default critical-failure demo.

## Default classification rules

| Condition | Status | Python action |
| --- | --- | --- |
| 0–100 ms | HEALTHY | Record the day and reset the lag streak. |
| 101–300 ms, consecutive lag below 3 | MINOR LAG | Record the warning and continue. |
| Third consecutive 101–300 ms reading | ESCALATED FAILURE | Record a failure and break. |
| Above 300 ms | CRITICAL FAILURE | Record a failure and immediately break. |

The critical-ping check has priority. A healthy reading resets the streak, so separated lag readings do not cause escalation. The thresholds are configurable teaching rules, not universal production standards.

## Network scenarios

| Scenario | Inclusive random range |
| --- | --- |
| Stable Network | 20–140 ms |
| Busy Network | 60–320 ms |
| Unstable Network | 80–450 ms |

Readings are uniform within the selected range. Changing thresholds changes classification, not these generated ranges. Fixed demonstrations use predefined readings instead of random generation.

## Terminal interface

Run these commands from the project folder:

    python main.py
    python main.py --scenario busy --days 14 --seed 42
    python main.py --demo
    python main.py --demo-lag
    python main.py --scenario busy --days 14 --seed 42 --healthy-limit 120 --critical-limit 350 --lag-limit 4
    python main.py --scenario busy --days 14 --seed 42 --csv-file logs/run.csv
    python main.py --help

The terminal defaults to seven days on a stable network. Use a seed only with random mode. Demos support at most seven planned days.

Custom log and history destinations are also supported:

    python main.py --scenario unstable --log-file logs/my_run.txt --history-dir logs/history

On Windows, **run_demo.bat** launches the critical-failure terminal demo.

## Logs, history and CSV format

The latest terminal report is saved to logs/server_uptime.log by default. Every completed run also receives a unique timestamped JSON record and text report under logs/history/. History remains on your computer and is excluded from Git.

The GUI uses the project folder for history; terminal paths are relative to the current working directory. The history viewer shows the latest 100 valid records. Changing the latest-log file does not replace separate historical records.

CSV export contains one row per checked day with these columns:

    day,ping_ms,status,lag_streak,action,healthy_limit,critical_limit,lag_limit

No unevaluated day is exported as though it had been checked.

## Expected demo results with default thresholds

| Demo | Checked | Healthy | Minor lag | Failures | Unevaluated | Healthy check rate |
| --- | --- | --- | --- | --- | --- | --- |
| Critical failure | 6 | 3 | 2 | 1 | 1 | 50% |
| Lag escalation | 4 | 1 | 2 | 1 | 3 | 25% |

Generated samples: [critical failure](examples/demo_output.txt) and [lag escalation](examples/lag_escalation_output.txt).

## Core algorithm

    FOR each requested day:
        obtain one simulated ping
        IF ping > critical limit:
            record critical failure
            BREAK
        IF ping > healthy limit:
            increase consecutive lag streak
            IF streak reaches lag limit:
                record escalated failure
                BREAK
            record minor lag
            CONTINUE
        reset lag streak
        record healthy day
    summarize checked days and save the completed run

Continue skips healthy-day processing. Break exits the monitoring loop. Summary and file-saving code after the loop still execute. The terminal consumes the same generator that the teaching mode advances one day at a time.

## Project files

| File | Purpose |
| --- | --- |
| main.py | Shared generator, simulation, statistics, reports, comparison, CSV and terminal CLI. |
| gui.py | Dark Tkinter dashboard, teaching controls, charts and history viewer. |
| run_gui.bat | Windows desktop launcher. |
| run_demo.bat | Windows terminal-demo launcher. |
| docs/PROJECT_REPORT.md | Project report and viva preparation. |
| examples/ | Generated demonstration logs. |
| tests/ | Simulation, terminal, persistence, export and desktop integration tests. |
| .github/workflows/python-tests.yml | Automated Linux and Windows checks. |

## Tests

    python -m unittest discover -s tests -v

Desktop tests are opt-in and require a graphical environment. In Windows PowerShell:

    $env:RUN_GUI_TESTS = "1"
    python -m unittest discover -s tests -v

Tests cover thresholds, lazy stepping, early stopping, statistics, CSV content, saved records, comparison and desktop integration. GitHub Actions checks core behaviour across Python versions and the desktop interface on Windows.

## Scope

This is a **Python simulation project**. It makes no real server ping requests, does not wait for real days, and does not train or run an AI model. Its healthy-check rate is a statistic over simulated checks, not measured production uptime.

## Repository

[GitHub: k-m-rahaman/Server_Uptime_Monitoring_Log](https://github.com/k-m-rahaman/Server_Uptime_Monitoring_Log)

    git clone https://github.com/k-m-rahaman/Server_Uptime_Monitoring_Log.git
    cd Server_Uptime_Monitoring_Log
    python gui.py
