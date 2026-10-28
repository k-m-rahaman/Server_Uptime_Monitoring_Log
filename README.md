# Server Uptime Monitoring Log

A third-semester AIML Python mini project that simulates one server ping reading per day. It demonstrates **`for` loops**, **random number generation**, **`continue`**, and **`break`** through a readable server-health log.

This is a simulation: it does not contact a server or wait for real days to pass. It does not use a machine-learning model.

## Objective

Generate daily ping statuses, skip the remaining processing for a minor lag spike using `continue`, and stop the monitoring loop on a critical failure using `break`.

## Requirements

- Python 3.10 or later
- A terminal or an editor such as VS Code
- No third-party packages

## Run the project

Open a terminal in the project folder and run:

```bash
python main.py
```

On Windows, use `py` instead of `python` if that is how Python is installed. You can also double-click `run_demo.bat` to launch the demonstration. The launcher checks `py`, `python`, and an available Codex Python runtime.

For a repeatable classroom demonstration:

```bash
python main.py --demo
```

For a random simulation with a chosen number of days:

```bash
python main.py --days 14
```

For a repeatable random run, supply a seed:

```bash
python main.py --days 14 --seed 42
```

Save the report to a custom location:

```bash
python main.py --demo --log-file logs/classroom_demo.log
```

The report is printed in the terminal and written to `logs/server_uptime.log` by default. Each run replaces the selected log file. A simulated critical failure is an expected result of the program; the summary identifies the failure and the unprocessed days.

Use `python main.py --help` to see the command-line options. `--days` must be a positive integer. Demo mode supports at most seven days. Use `--seed` with random mode; it cannot be combined with `--demo`.

## Status rules

| Ping value | Status | Action |
| --- | --- | --- |
| 0–100 ms | `HEALTHY` | Record a healthy day and finish that iteration. |
| 101–300 ms | `MINOR LAG` | Record the lag, then use `continue` to move to the next day. |
| Above 300 ms | `CRITICAL FAILURE` | Record the failure, then use `break` to stop the loop immediately. |

Random mode generates integer values from **20 to 350 ms**, inclusive. These thresholds are classroom rules selected for this simulation, not universal production monitoring standards.

## Demo results

Demo mode supplies these readings in order:

```text
45, 160, 72, 100, 300, 301, 55
```

| Day | Ping | Result |
| --- | --- | --- |
| 1 | 45 ms | Healthy |
| 2 | 160 ms | Minor lag; continue to the next day |
| 3 | 72 ms | Healthy |
| 4 | 100 ms | Healthy; demonstrates the upper healthy boundary |
| 5 | 300 ms | Minor lag; demonstrates the upper lag boundary |
| 6 | 301 ms | Critical failure; stop monitoring |
| 7 | — | Not evaluated because day 6 stopped the loop |

The summary contains **6 checked days, 3 healthy days, 2 lag days, 1 critical failure, and 1 unevaluated day**. The healthy check rate is `3 / 6 × 100 = 50%`.

See [the complete demo output](examples/demo_output.txt). The healthy check rate counts only performed simulated checks; it is not a measured uptime percentage over real time.

## How the program works

1. Read and validate the command-line options.
2. Start a `for` loop over the requested days.
3. Generate a random ping value, or read the next fixed demo value.
4. Log a critical value and `break` if it exceeds 300 ms.
5. Log a minor lag and `continue` if it exceeds 100 ms.
6. Record a healthy value when neither condition applies.
7. Print the final summary and save the report to a text file.

The failure check comes first so that a ping above 300 ms cannot be classified as minor lag.

## Project files

```text
server-uptime-monitoring-log/
├── main.py                  # Simulation and command-line interface
├── README.md                # Setup, usage, and explanation
├── docs/
│   └── PROJECT_REPORT.md    # Submission report and viva preparation
├── examples/
│   └── demo_output.txt      # Reproducible demonstration output
└── tests/                   # Automated behaviour checks
```

The `logs/` folder is generated when the program runs. Generated logs and Python cache files are excluded from Git.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

Tests check the status boundaries, the behaviour after lag spikes, immediate stopping on failure, and reproducible random runs.

## GitHub repository

Repository: [k-m-rahaman/Server_Uptime_Monitoring_Log](https://github.com/k-m-rahaman/Server_Uptime_Monitoring_Log)

To download and run a fresh copy:

```bash
git clone https://github.com/k-m-rahaman/Server_Uptime_Monitoring_Log.git
cd Server_Uptime_Monitoring_Log
python main.py --demo
```

After making your own changes, review, commit, and push:

```bash
git status
git add .
git commit -m "Update monitoring project"
git push origin main
```

Authenticate using GitHub's normal sign-in flow when prompted. Do not put passwords or access tokens in source files. GitHub Actions runs the tests and classroom demo on Python 3.10, 3.12, and 3.13 for pushes and pull requests.

## Presentation checklist

1. Introduce the objective and the three ping categories.
2. Run `python main.py --demo` and explain each status.
3. Point to the `for`, `continue`, and `break` statements in `main.py`.
4. Explain why the seventh demo reading is never processed.
5. Show the saved log and run the tests.
6. Run `python main.py --days 10` to show random simulation.

For the algorithm, limitations, and viva questions, read [the project report](docs/PROJECT_REPORT.md).
