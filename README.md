# Pulse — Server Uptime Monitoring Log

A third-semester AIML Python mini project with a desktop dashboard and terminal interface. It demonstrates **for loops, random numbers, continue and break**. Both interfaces use the same Python simulation.

## Start the interface

On Windows, double-click **run_gui.bat**, or run this in the project folder:

    python gui.py

Requirements: **Python 3.10+ with Tkinter**. No pip packages are required. Tkinter is normally included with the official Windows Python installer. On Linux, install your distribution's Tkinter package if needed, such as python3-tk on Debian/Ubuntu. Check availability with:

    python -m tkinter

The Windows launchers try py, python and an available Codex Python runtime. A display of 1280 × 800 or larger is recommended. **Expand log** gives the event table more space on a smaller display.

## Dashboard features

- Stable, busy and unstable network scenarios.
- Adjustable simulated days and an optional random seed.
- Two fixed classroom demos for immediate failure and repeated-lag escalation.
- Colour-coded daily log showing ping, status, lag streak and loop action.
- Ping chart with threshold lines and a status-distribution summary.
- Exact stop reason and count of unevaluated days.
- Separate saved run history, a history viewer and text export.

Rows play back briefly for presentation. **Finish playback** reveals the complete result immediately. The underlying Python loop has already made every decision.

## Classroom demonstration

1. Select **Critical failure demo** and click **Run simulation**. Minor lag continues; the 301 ms reading on day 6 stops monitoring. Day 7 is never evaluated.
2. Select **Lag escalation demo** and run again. The first two consecutive lag days continue; the third triggers a failure on day 4.
3. Use **Expand log**, **History** and **Export log** to inspect the results.
4. Choose **Random scenario** to compare network conditions. The same scenario, seed and days reproduce the same results.

## Simulation rules

| Condition | Status | Action |
| --- | --- | --- |
| 0–100 ms | HEALTHY | Record the day and reset the lag streak. |
| 101–300 ms, streak 1 or 2 | MINOR LAG | Record the warning and continue. |
| Third consecutive 101–300 ms reading | ESCALATED FAILURE | Record one failure and break. |
| Above 300 ms | CRITICAL FAILURE | Record one failure and immediately break. |

The critical-ping check has priority. The third consecutive lag reading counts in the **failure** category, so healthy + minor lag + failure equals the number of checked days. A run has at most one failure.

| Scenario | Inclusive random ping range |
| --- | --- |
| Stable Network | 20–140 ms |
| Busy Network | 60–320 ms |
| Unstable Network | 80–450 ms |

Readings are uniform within each range. A stable scenario can still fail through consecutive lag. Fixed demos bypass random generation and scenario ranges. These are classroom rules, not universal production thresholds.

## Terminal commands

    python main.py
    python main.py --scenario busy --days 14 --seed 42
    python main.py --demo
    python main.py --demo-lag
    python main.py --scenario unstable --log-file logs/my_run.txt --history-dir logs/history
    python main.py --help

Default: 7 simulated days on a stable network. Days must be positive; the dashboard supports 1–365 and demos support at most 7. Use a seed only with random mode. On Windows, **run_demo.bat** launches the critical-failure terminal demo.

## Logs and history

The latest terminal report is written to logs/server_uptime.log by default. Every completed terminal or dashboard run also gets a unique timestamped JSON record and text report under logs/history/. The GUI uses the project folder; terminal paths are relative to your working directory.

History remains on your computer and is excluded from Git. The selected latest-log file can be replaced; historical records are preserved separately. The history viewer shows the latest 100 valid records. **Export log** saves the current GUI report to a chosen text file.

## Expected demo results

| Demo | Checked | Healthy | Minor lag | Failures | Unevaluated |
| --- | --- | --- | --- | --- | --- |
| Critical failure | 6 | 3 | 2 | 1 | 1 |
| Lag escalation | 4 | 1 | 2 | 1 | 3 |

Generated samples: [critical failure](examples/demo_output.txt) and [lag escalation](examples/lag_escalation_output.txt).

**Healthy check rate = healthy days ÷ checked days × 100.** This is a simulation statistic, not measured service uptime. The project makes no network requests, does not wait real days, and does not use a machine-learning model.

## Core algorithm

    FOR each requested day:
        generate a ping from the chosen scenario
        IF ping > 300:
            record critical failure
            BREAK
        IF ping > 100:
            increase consecutive lag streak
            IF streak == 3:
                record escalated failure
                BREAK
            record minor lag
            CONTINUE
        reset lag streak
        record healthy day
    summarize and save the run

Continue skips healthy-day processing. Break exits the monitoring loop. The summary and file-saving code after the loop still execute.

## Project files

| File | Purpose |
| --- | --- |
| main.py | Shared simulation, text reporting, history and terminal CLI. |
| gui.py | Tkinter dashboard, charts and history viewer. |
| run_gui.bat | Windows desktop launcher. |
| run_demo.bat | Windows terminal-demo launcher. |
| docs/PROJECT_REPORT.md | Submission report and viva preparation. |
| examples/ | Generated demo logs. |
| tests/ | Simulation, CLI, persistence and desktop tests. |
| .github/workflows/python-tests.yml | Automated Linux and Windows checks. |

## Tests

    python -m unittest discover -s tests -v

Desktop tests are opt-in and require a graphical environment. In Windows PowerShell:

    $env:RUN_GUI_TESTS = "1"
    python -m unittest discover -s tests -v

Tests cover boundaries, lazy stopping, streak reset and escalation, scenario ranges, seeded repeatability, history, terminal output and desktop integration. GitHub Actions checks core behaviour on Python 3.10, 3.12 and 3.13, plus desktop integration on Windows with Python 3.12.

## GitHub

Repository: [k-m-rahaman/Server_Uptime_Monitoring_Log](https://github.com/k-m-rahaman/Server_Uptime_Monitoring_Log)

    git clone https://github.com/k-m-rahaman/Server_Uptime_Monitoring_Log.git
    cd Server_Uptime_Monitoring_Log
    python gui.py

Read [the project report](docs/PROJECT_REPORT.md) for submission notes and viva questions. Add your student details to your submission copy.
