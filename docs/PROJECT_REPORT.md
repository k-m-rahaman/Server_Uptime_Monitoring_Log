# Server Uptime Monitoring Log

**Course context:** Third-semester AIML — Python fundamentals mini project

**Language:** Python 3.10+

**Project type:** Command-line simulation

Add your name, roll number, section, institution, and faculty details to your submission copy as required.

## Abstract

This project simulates daily server ping readings and produces a server-health log. A `for` loop represents consecutive days. Random integer values represent response times, and conditional statements classify them as healthy, minor lag, or critical failure. The program uses `continue` to bypass the remaining processing for a minor lag spike and `break` to halt monitoring when a critical failure occurs. It displays a summary and saves the report to a text file. A fixed demonstration mode makes every control-flow case reproducible.

## Objective

Use `for` loops and random number generation to simulate daily server ping statuses, use `continue` for minor lag spikes, and use `break` to stop execution of the monitoring loop on critical failures.

## Expected outcome

A simulated log that accurately assigns statuses according to the project's thresholds, resumes with the next day after minor lag, and stops evaluating new days immediately after a critical failure. A summary shows the number of performed checks and each status count.

## Tools and requirements

| Item | Requirement |
| --- | --- |
| Runtime | Python 3.10 or later |
| Interface | Terminal or command prompt |
| Libraries | Python standard library only |
| Storage | Local text log file |
| Version control | Git and a GitHub repository for submission |

No internet connection is needed to run the simulation. GitHub access is needed only to publish or download the repository.

## Concepts demonstrated

| Concept | Use in the project |
| --- | --- |
| `for` and `range` | Represent the requested sequence of days. |
| Random number generation | Generate simulated ping values between 20 and 350 ms. |
| `if` conditions | Compare readings with the health thresholds. |
| `continue` | Skip the rest of the minor-lag iteration and start the next day. |
| `break` | Exit the monitoring loop on a critical failure. |
| Functions | Separate simulation, report formatting, and command-line handling. |
| Lists and dictionaries | Store the readings, statuses, and summary counts. |
| File handling | Save the formatted report for later inspection. |
| Input validation | Reject invalid command-line inputs. |

## Classification rules

| Ping response time | Classification | Control flow |
| --- | --- | --- |
| 0–100 ms | Healthy | Complete normal processing for the day. |
| 101–300 ms | Minor lag | Record the lag, then `continue`. |
| Above 300 ms | Critical failure | Record the failure, then `break`. |

The simulation generates only non-negative integer readings. The failure threshold is checked before the lag threshold. Otherwise, a value such as 301 ms could be incorrectly handled by a broader condition such as `ping > 100`.

These are chosen teaching thresholds. A real monitoring system would select thresholds for its network and service requirements.

## Algorithm

1. Start the program.
2. Read the requested number of days, optional random seed, demo option, and log-file path.
3. Validate the options.
4. Initialize the entries and status counters.
5. For each day from 1 through the requested number of days:
   - Obtain the next simulated ping reading.
   - If the reading is greater than 300 ms, record a critical failure and exit the loop with `break`.
   - If the reading is greater than 100 ms, record minor lag and advance to the next iteration with `continue`.
   - Otherwise, record a healthy day.
6. Calculate performed checks, unprocessed days, and the healthy check rate.
7. Format the complete report, display it, and write it to the selected file.
8. End the program.

Pseudocode for the central loop:

```text
FOR day FROM 1 TO requested_days
    ping = next simulated reading

    IF ping > 300
        record CRITICAL FAILURE
        BREAK
    END IF

    IF ping > 100
        record MINOR LAG
        CONTINUE
    END IF

    record HEALTHY
END FOR
```

`break` ends the loop. The report and file-saving code after the loop still execute. `continue` ends only the current iteration; the next day can still be checked.

## Program structure

The simulation function is:

```python
monitor_server(days=7, seed=None, ping_values=None)
```

It returns a dictionary containing:

| Field | Meaning |
| --- | --- |
| `requested_days` | Number of simulated days requested. |
| `entries` | Performed checks, each with `day`, `ping_ms`, and `status`. |
| `healthy_days` | Number of healthy readings. |
| `lag_days` | Number of minor-lag readings. |
| `critical_days` | Number of critical failures; at most one per run. |
| `stopped_early` | Whether a failure prevented checking remaining requested days. |

Supplying a seed makes a random run repeatable. Supplying `ping_values` allows fixed demo readings and precise tests of status boundaries and stopping behaviour.

## Execution and sample result

Run the fixed demonstration:

```bash
python main.py --demo
```

The planned readings are `45, 160, 72, 100, 300, 301, 55` ms. The first six produce the following results:

| Day | Ping | Status |
| --- | --- | --- |
| 1 | 45 ms | Healthy |
| 2 | 160 ms | Minor lag |
| 3 | 72 ms | Healthy |
| 4 | 100 ms | Healthy |
| 5 | 300 ms | Minor lag |
| 6 | 301 ms | Critical failure |

The seventh reading is not evaluated. The final counts are:

- Requested days: 7
- Checked days: 6
- Healthy days: 3
- Minor-lag days: 2
- Critical failures: 1
- Unevaluated days: 1
- Healthy check rate: `3 ÷ 6 × 100 = 50%`

The full generated sample is available in [examples/demo_output.txt](../examples/demo_output.txt). The default saved report is `logs/server_uptime.log`.

For random simulation:

```bash
python main.py --days 10
```

For repeatable random simulation:

```bash
python main.py --days 10 --seed 42
```

## Testing

Run the automated tests from the project folder:

```bash
python -m unittest discover -s tests -v
```

The important behaviour to verify is:

| Case | Expected behaviour |
| --- | --- |
| 100 ms | Healthy |
| 101 ms | Minor lag |
| 300 ms | Minor lag |
| 301 ms | Critical failure |
| Healthy reading after lag | The next day is still processed. |
| Reading after critical failure | It is never processed. |
| No critical reading | All requested days are processed. |
| Same seed and options | The random results repeat. |
| Invalid number of days | Input is rejected with a clear message. |

## Limitations

- Readings are generated locally; the program sends no network requests.
- Each iteration represents a simulated day. The program does not wait 24 hours between iterations.
- A high response time is treated as a critical failure by the assignment's rule. It does not prove that a real server is offline.
- The healthy check rate describes the simulated checks performed. It is not an accurate measurement of service uptime over time.
- Monitoring stops after one critical failure. Recovery, retries, and alerts are outside the current project.
- The project demonstrates Python control flow; it does not train or run an AI model.

## Possible future improvements

Add configurable thresholds, real network measurements, timestamps, recovery checks, and a graphical view of historical logs. Each extension would require a clear definition of what counts as availability and how often the server is measured.

## Viva preparation

**Why is a `for` loop used?**

The number of planned simulated days is known before the run, so a `for` loop can iterate over that range.

**What does `continue` do here?**

It moves directly to the next day after a minor lag has been recorded. The lag day is counted, but healthy-day processing is skipped.

**What does `break` do here?**

It exits the monitoring loop immediately after a critical failure is recorded. Later readings are not evaluated.

**Why check for critical failure first?**

Critical readings also exceed the minor-lag threshold. Checking the stricter condition first prevents misclassification.

**What happens at exactly 100 ms and 300 ms?**

100 ms is healthy; 300 ms is minor lag. A reading must be greater than 300 ms to trigger a critical failure.

**Why include a random seed?**

It makes random runs repeatable for demonstrations and debugging.

**Why include a fixed demo mode?**

An uncontrolled random run may not show every required status. Demo mode reliably shows healthy readings, minor lag, and a critical failure.

**Does `break` prevent the summary from appearing?**

No. It exits the loop, and execution continues with the report code after the loop.

**Does the program measure real server uptime?**

No. It simulates readings to demonstrate the assignment's programming concepts.

## Submission checklist

- Fill in your student details in the report copy required by your institution.
- Run demo mode and understand each output line.
- Confirm that the saved log matches the terminal report.
- Run the automated tests.
- Push the source, README, sample output, and report to your GitHub repository.
- Submit the repository URL and any report or output screenshots requested by your faculty.
