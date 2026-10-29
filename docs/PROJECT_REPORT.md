# Pulse — Server Uptime Monitoring Log

**Python Project | Semester 3 | Section J | Group 1**

## Group members

1. Kazi Mustafijur Rhaman
2. Anisha Akhtar
3. Koyel Basu
4. Suraiya Yeasmin

## Abstract

Pulse is a Python desktop and command-line project that simulates daily server health. A for loop represents planned days, random integers model ping response times, continue bypasses healthy processing after minor lag, and break halts monitoring on failure. The dark Tkinter dashboard shows charts, a colour-coded event log and an exact stop reason.

The project includes a lazy step-by-step teaching mode, configurable health thresholds, checked-day statistics, saved-run comparison and CSV export. These additions support classroom explanation while keeping the original Python control-flow objective central.

## Objective and expected outcome

Use for loops and random number generation to simulate daily server ping statuses, continue to bypass minor lag spikes, and break to halt checks on a critical failure.

The expected outcome is an accurate simulated log that classifies each checked day, advances after ordinary lag, and never evaluates later days after a failure. Completed results can be inspected, compared and exported for a report.

## Tools and architecture

| Component | Purpose |
| --- | --- |
| Python 3.10+ | Application language. |
| Tkinter | Desktop dashboard and teaching controls. |
| random.Random | Seeded, independent random generation. |
| main.py | Shared generator, summaries, history, comparison, CSV and CLI. |
| gui.py | Dashboard, charts, settings and history interaction. |
| Lists and dictionaries | Daily entries and final reports. |
| json, pathlib, datetime and uuid | Separate timestamped run records. |
| csv | Spreadsheet-ready export of checked days. |
| unittest | Behaviour and integration checks. |
| Git and GitHub Actions | Version control and automated validation. |

All application dependencies are from the Python standard library. Tkinter and a graphical environment are needed for the dashboard; no pip packages are required.

## Simulation rules

The default healthy limit is 100 ms, critical limit is 300 ms and consecutive-lag limit is 3.

| Condition | Result | Control flow |
| --- | --- | --- |
| Ping at or below healthy limit | Healthy; reset the lag streak. | Normal processing. |
| Ping above healthy limit but not above critical limit, before the lag limit | Minor lag; increase the streak. | Continue. |
| Consecutive lag streak reaches its limit | Escalated failure. | Break. |
| Ping above critical limit | Immediate critical failure. | Break. |

A critical ping is checked first because it also exceeds the ordinary lag threshold. A healthy day resets the streak. The terminal lag reading that reaches the escalation limit counts as a failure rather than also counting as ordinary minor lag. Therefore, category counts sum to performed checks.

Custom thresholds must be whole numbers satisfying 0 ≤ healthy limit < critical limit, with a consecutive-lag limit of at least 1. Thresholds change classification but do not change the selected random scenario's range.

## Network scenarios

| Network | Inclusive random range |
| --- | --- |
| Stable Network | 20–140 ms |
| Busy Network | 60–320 ms |
| Unstable Network | 80–450 ms |

Readings are uniform within the chosen range. A stable scenario can still fail through repeated lag. Fixed demos bypass random generation and scenario ranges.

## Shared lazy generator

The central generator is iter_monitor(). Its for loop obtains and processes one reading when advanced. It yields a daily entry and eventually returns the final report. monitor_server() consumes the same generator to provide a complete terminal result.

The dashboard teaching mode advances this generator using Next Day. This is actual incremental execution, not playback of a previously completed calculation. The generator does not consume future input before the next step and never consumes another reading after a terminal failure.

Each entry includes its day, ping, status, lag streak, action, explanation and highlighted control-flow statement.

## Algorithm

1. Read and validate days, scenario, seed and thresholds.
2. Initialize entries, status counts and the consecutive-lag streak.
3. Iterate over requested days with a for loop.
4. Obtain one random ping or fixed demonstration reading.
5. If the ping exceeds the critical limit, record a critical failure and exit with break; present the entry afterward.
6. If the ping exceeds the healthy limit, increase the streak:
   - If the streak reaches the configured lag limit, record escalation and break; present the entry afterward.
   - Otherwise record minor lag and continue; present the entry before obtaining the next reading.
7. Otherwise reset the streak, record a healthy day and present its entry before another reading is obtained.
8. Summarize only the checks actually performed.
9. Save the completed run and provide text or CSV output when requested.

The summary still appears after break because it is outside the monitoring loop. Continue skips the remaining healthy-day processing within one iteration.

## Dashboard and teaching features

The original dark dashboard layout contains scenario controls, four summary cards, a ping chart, distribution bars, a daily event table and a status area.

- **Step-by-step teaching:** Enable the option, start a run and use Next Day to advance. A teaching pane highlights for, continue or break and explains the current decision.
- **Thresholds...:** Set healthy, critical and consecutive-lag limits, or use Reset defaults.
- **Statistics:** View average ping, highest ping and longest lag streak for checked days.
- **History and Compare:** Select exactly two saved runs with Ctrl+click and compare their settings, counts, statistics and stop reasons side by side.
- **Export CSV:** Save processed daily rows and the thresholds used.
- **Finish playback:** Complete remaining checks immediately under the same rules.
- **Expand log:** Hide chart panels temporarily to make more event rows visible.
- **Export log:** Save a readable text report.

Fixed demos plan seven days. The dashboard initially plans fourteen days for random mode and supports 1–365 days. The optional seed repeats random results when scenario, days and thresholds also match.

## Execution

On Windows, open the project folder and double-click run_gui.bat. In a terminal:

    python gui.py

In VS Code, select File → Open Folder, choose the folder containing main.py and gui.py, open Terminal → New Terminal, and run:

    .\run_gui.bat

Terminal examples:

    python main.py --scenario busy --days 14 --seed 42
    python main.py --demo
    python main.py --demo-lag
    python main.py --scenario busy --days 14 --seed 42 --healthy-limit 120 --critical-limit 350 --lag-limit 4
    python main.py --scenario busy --csv-file logs/run.csv

The terminal defaults to seven days on a stable network. A seed is used only with random mode. Demos support at most seven requested days. Changing thresholds can change fixed-demo outcomes.

## Demonstration results with default thresholds

### Immediate critical failure

The readings are 45, 160, 72, 100, 300, 301 and 55 ms. Day 6 exceeds 300 ms and ends the loop. Day 7 is never checked.

### Repeated-lag escalation

The readings are 65, 180, 240, 280, 55, 80 and 90 ms. Days 2 and 3 record lag and continue. Day 4 is the third consecutive lag reading and ends the loop. Days 5–7 are not checked.

| Demo | Checked | Healthy | Minor lag | Failures | Unevaluated | Healthy check rate |
| --- | --- | --- | --- | --- | --- | --- |
| Critical failure | 6 | 3 | 2 | 1 | 1 | 50% |
| Lag escalation | 4 | 1 | 2 | 1 | 3 | 25% |

Full logs: [critical failure](../examples/demo_output.txt) and [lag escalation](../examples/lag_escalation_output.txt).

## Statistics

- Average ping = sum of checked ping values / number of checked days.
- Highest ping = maximum among checked readings.
- Longest lag streak = highest consecutive-lag count observed, including a terminal escalated-lag reading.
- Healthy check rate = healthy days / checked days × 100.

No reading after failure enters these calculations. Before any check, average and highest ping have no value. A failure on the final requested day is still a failure, but stopped_early is false because no remaining days were prevented.

The critical_days report field counts both immediate critical failure and escalated failure for compatibility with the initial project.

## Persistence, comparison and export

Each completed run receives a unique timestamped JSON record and readable text report under logs/history/. The record includes thresholds, seed, scenario, source, entries, statistics, counters and the stop reason.

The history viewer displays the latest 100 valid records. Earlier records without threshold or statistics fields remain usable: original threshold defaults are assumed and statistics can be derived from their checked entries. Damaged records are skipped so other runs remain accessible.

Comparisons show two saved runs side by side. Differences in checked counts may result from different settings or stopping conditions; the comparison does not invent readings for unevaluated days.

CSV export contains these columns:

    day,ping_ms,status,lag_streak,action,healthy_limit,critical_limit,lag_limit

There is one row per processed day. Separate historical records remain preserved when the latest terminal text-log file is replaced. Generated logs and history remain local and are excluded from Git.

## Testing

Run:

    python -m unittest discover -s tests -v

Optional desktop integration checks require a graphical environment. In Windows PowerShell:

    $env:RUN_GUI_TESTS = "1"
    python -m unittest discover -s tests -v

Tests cover default and custom boundaries, input validation, lazy stepping, continuation and stopping, checked-only statistics, seeded repeatability, historical compatibility, side-by-side comparison, CSV content and GUI integration. GitHub Actions also checks the project across Python versions and on Windows.

## Limitations

The project generates readings locally. It makes no real network ping requests, does not wait actual days and does not train or run an AI model. Its thresholds are teaching rules, and healthy-check percentage is not real-world server uptime. Recovery checks, retries and external alerts are outside its scope.

## Viva preparation

**Why a for loop?** The planned number of days is known before execution.

**What does continue do?** It bypasses healthy processing after ordinary minor lag and advances to the next day.

**What does break do?** It exits the loop and abandons later checks after failure.

**Why check critical ping first?** A reading above the critical limit is also above the healthy limit, so the stricter rule must have priority.

**Why reset the streak after a healthy day?** The escalation rule concerns consecutive lag, not the total number of lag days.

**How does teaching mode stay within the topic?** It advances the same Python for loop one iteration at a time and shows the actual continue or break decision.

**Why are thresholds configurable?** They demonstrate how changing conditions changes control flow while leaving the algorithm's structure intact.

**Why calculate statistics from checked days only?** Later days were not processed and have no observed simulated result.

**Why save settings with CSV and history?** The numbers can be interpreted and compared only when the rules used to classify them are known.

**What is the purpose of a seed?** It makes random runs repeatable for demonstrations and comparisons.

## Submission checklist

1. Introduce the project as the Semester 3, Section J, Group 1 Python project.
2. Present the four group members.
3. Demonstrate default critical and escalation failures.
4. Use Next Day to explain for, continue and break.
5. Change thresholds and explain the resulting difference.
6. Show checked-day statistics, compare two saved runs and export CSV.
7. Run the tests and submit the repository link with any required faculty screenshots.
