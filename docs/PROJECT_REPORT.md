# Server Uptime Monitoring Log — Pulse

**Course:** Third-semester AIML, Python fundamentals mini project

**Language:** Python 3.10+ with Tkinter; standard library only

**Student details:** Add your name, roll number, section, institution and faculty details to your submission copy.

## Abstract

Pulse simulates daily server ping readings and classifies them as healthy, minor lag or failure. A for loop represents planned days. Random integers model response times for three network scenarios. Continue bypasses healthy processing after minor lag. Break stops the loop after an immediate critical reading or three consecutive lag spikes. A Tkinter dashboard displays charts, an event log, an exact stop reason and saved run history.

## Objective and outcome

Use for loops and random number generation to simulate daily server ping statuses, continue for minor lag spikes, and break for critical failures. The expected outcome is an accurate simulated log that stops evaluating later days when a failure rule is met.

Scenario selection, consecutive-lag escalation and the dashboard extend the same control-flow topic without requiring machine learning or real networking.

## Architecture and concepts

| Component | Purpose |
| --- | --- |
| main.py | Shared simulation, report formatting, history persistence and terminal interface. |
| gui.py | Tkinter controls, charts, table, presentation playback and history viewer. |
| random.Random | Local seeded random integers, independent of global random state. |
| Lists and dictionaries | Per-day entries and final summary fields. |
| pathlib, json, datetime, uuid | Separate timestamped text and JSON records. |
| unittest | Behaviour, terminal, persistence and optional desktop integration checks. |
| GitHub Actions | Checks across Python versions and Windows desktop integration. |

The GUI calls monitor_server() from main.py. It does not duplicate the health-classification rules. Python calculates the simulation; Tkinter's after() method then reveals the resulting rows without blocking the interface.

## Rules

| Condition | Classification and control flow |
| --- | --- |
| 0–100 ms | Healthy; reset lag streak and complete the iteration. |
| 101–300 ms, streak 1 or 2 | Minor lag; record and continue. |
| Third consecutive 101–300 ms reading | Escalated failure; record and break. |
| Above 300 ms | Immediate critical failure; record and break. |

Critical ping is checked first because it also exceeds the ordinary lag threshold. A healthy day resets the streak. The third consecutive lag day is counted as a failure, not also as a minor-lag day. Healthy + minor lag + failure therefore equals the number of performed checks.

## Scenarios

| Network | Inclusive random range |
| --- | --- |
| Stable | 20–140 ms |
| Busy | 60–320 ms |
| Unstable | 80–450 ms |

Readings are uniform within the selected range. Stable networks can still fail through repeated lag. These teaching scenarios are not calibrated network models. Fixed demonstrations intentionally bypass random generation and scenario ranges.

## Algorithm

1. Read and validate the days, scenario, optional seed and mode.
2. Initialize entries, counters and the consecutive-lag streak.
3. Iterate from day 1 through the requested last day using a for loop.
4. Generate one random ping or obtain one fixed demo reading.
5. If ping exceeds 300 ms, record the reason and critical failure, then break.
6. If ping exceeds 100 ms, increase the lag streak. On the third consecutive lag, record escalation and break. Otherwise record minor lag and continue.
7. Otherwise reset the streak and record a healthy day.
8. Summarize performed checks, category counts, unevaluated days, maximum lag streak and healthy-check rate.
9. Display the result and save a separate historical record and text report.

Break exits the loop; summary code after the loop still executes. Continue ends only the current iteration and bypasses healthy-day processing.

## Interface and execution

Start with python gui.py or double-click run_gui.bat on Windows. Python 3.10+ with Tkinter and a graphical environment is required. No pip packages are needed. A 1280 × 800 display is recommended.

The sidebar first asks for a run mode, then shows its settings. The critical-failure demo is selected for a predictable first run. Random mode enables scenario and days (1–365); the optional repeat-number field appears only when requested. Fixed demos use seven planned days and disable irrelevant random settings. The dashboard shows counters, a ping chart, threshold lines, distribution bars, a colour-coded event table, exact stop reason and progress.

Show all results now skips the presentation delay without changing the result. Daily results is the default tab, and selecting a row explains its decision. Charts & summary contains the graphs. Saved runs opens history, and Save log... writes a selected text file.

Terminal commands:

    python main.py --scenario busy --days 14 --seed 42
    python main.py --demo
    python main.py --demo-lag

## Demonstration results

The critical-failure demo uses 45, 160, 72, 100, 300, 301, 55 ms. Day 6 fails immediately; day 7 is never evaluated.

The escalation demo uses 65, 180, 240, 280, 55, 80, 90 ms. Days 2 and 3 continue after lag. Day 4 is the third consecutive lag, so monitoring stops and days 5–7 are not evaluated.

| Demo | Checked | Healthy | Minor lag | Failures | Unevaluated | Healthy check rate |
| --- | --- | --- | --- | --- | --- | --- |
| Critical failure | 6 | 3 | 2 | 1 | 1 | 50% |
| Lag escalation | 4 | 1 | 2 | 1 | 3 | 25% |

See the full [critical-failure log](../examples/demo_output.txt) and [escalation log](../examples/lag_escalation_output.txt).

## Calculations and persistence

Healthy check rate = healthy days / checked days × 100.

Only performed checks enter the calculation. A failure on the final requested day counts as a failure, but stopped_early is false because no remaining days were prevented. The original critical_days report field now counts both kinds of terminal failure.

Each completed run receives a unique timestamped JSON record and text report in logs/history/. Records store entries, scenario, seed, source, counters and stop reason. The GUI shows the latest 100 valid records and skips damaged files. Generated history remains local and is excluded from Git.

The terminal additionally updates logs/server_uptime.log by default. The optional latest-log destination may be overwritten, while separate historical records are preserved.

## Testing

Run python -m unittest discover -s tests -v. Optional desktop tests require RUN_GUI_TESTS=1 and a graphical environment.

Checks cover 100/101/300/301 ms boundaries, continuing after lag, immediate and escalated stopping without reading later values, healthy-day streak reset, scenario ranges, seeded repeatability, separate saved records, terminal output and validation, and desktop integration. GUI checks cover summaries, charts, tables, history, repeated runs and supported window layout.

## Limitations

Readings are generated locally. No real server is contacted, no real days pass, and no AI model is trained or used. High ping and repeated lag are treated as failures only by the defined teaching rules. Healthy-check percentage is not measured real-world uptime. Recovery checks, retries and real alerts are outside this project.

## Viva preparation

**Why a for loop?** The planned number of days is known before execution.

**What does continue do?** It bypasses healthy processing after ordinary minor lag and advances to the next day.

**What does break do?** It abandons all remaining checks immediately after a failure.

**Why check critical ping first?** A reading over 300 is also over 100, so the stricter rule must have priority.

**Why reset the streak after a healthy day?** The escalation rule concerns consecutive lag, not the total number of lag days.

**What happens at exactly 100 and 300 ms?** 100 is healthy. 300 is lag and can escalate if it is the third consecutive lag. 301 fails immediately.

**Why use a seed?** It repeats the same random simulation for debugging and comparisons.

**Why fixed demos?** An uncontrolled random run may not show every required case.

**Does the GUI change the loop logic?** No. It calls the shared Python simulation and presents its results.

**What makes the project distinctive?** Scenario comparisons, streak-based escalation, precise stop explanations, charts and persistent run history extend the original loop-control objective.

## Submission checklist

Fill in student details, run both demos, explain both failure rules, point to for/continue/break in main.py, show saved history, run the tests, and submit the GitHub URL with any faculty-requested screenshots.
