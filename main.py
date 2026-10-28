"""Server Uptime Monitoring Log: a Python loop and random-number simulation."""

import argparse
import csv
import json
import random
from datetime import datetime
from pathlib import Path
from uuid import uuid4


DEMO_PINGS = [45, 160, 72, 100, 300, 301, 55]
LAG_DEMO_PINGS = [65, 180, 240, 280, 55, 80, 90]
HEALTHY_LIMIT = 100
CRITICAL_LIMIT = 300
LAG_LIMIT = 3
SCENARIOS = {
    "stable": {"name": "Stable Network", "range": (20, 140)},
    "busy": {"name": "Busy Network", "range": (60, 320)},
    "unstable": {"name": "Unstable Network", "range": (80, 450)},
}


def validate_settings(days, scenario, healthy_limit, critical_limit, lag_limit):
    """Reject invalid days and thresholds before a reading is generated."""
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("days must be a positive integer")
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ValueError("scenario must be stable, busy or unstable")
    for name, value in [("healthy_limit", healthy_limit),
                        ("critical_limit", critical_limit), ("lag_limit", lag_limit)]:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if not 0 <= healthy_limit < critical_limit:
        raise ValueError("Thresholds must satisfy 0 <= healthy_limit < critical_limit")
    if lag_limit < 1:
        raise ValueError("lag_limit must be at least 1")


def iter_monitor(days=7, seed=None, ping_values=None, scenario="stable",
                 healthy_limit=HEALTHY_LIMIT, critical_limit=CRITICAL_LIMIT,
                 lag_limit=LAG_LIMIT):
    """Yield one processed day at a time and return the final report.

    Calling next() is the only operation that obtains another reading. This
    lets the dashboard teach the real Python loop one day at a time.
    """
    validate_settings(days, scenario, healthy_limit, critical_limit, lag_limit)
    rng = random.Random(seed)
    readings = iter(ping_values) if ping_values is not None else None
    entries = []
    healthy_days = 0
    lag_days = 0
    critical_days = 0
    lag_streak = 0
    stop_reason = "All requested days were checked."
    failure_type = None
    pending_entry = None

    # FOR visits each simulated day. No real time delay or network is needed.
    for day in range(1, days + 1):
        # Present the previous day only after its control-flow action executed.
        # The current day's reading is still untouched until the next call.
        if pending_entry is not None:
            yield pending_entry
            pending_entry = None
        if readings is None:
            ping_ms = rng.randint(*SCENARIOS[scenario]["range"])
        else:
            try:
                ping_ms = next(readings)
            except StopIteration as error:
                raise ValueError("Not enough ping values for the requested days") from error
        if isinstance(ping_ms, bool) or not isinstance(ping_ms, int) or ping_ms < 0:
            raise ValueError("Each ping must be a non-negative integer in milliseconds")

        if ping_ms > critical_limit:
            stop_reason = (f"Day {day}: ping {ping_ms} ms exceeded the "
                           f"{critical_limit} ms critical threshold.")
            failure_type = "critical_ping"
            critical_days += 1
            entry = {
                "day": day, "ping_ms": ping_ms, "status": "CRITICAL FAILURE",
                "lag_streak": 0, "action": "break", "highlight": "break",
                "explanation": (f"{ping_ms} ms is above {critical_limit} ms. "
                                "The break statement exits the loop; later days are not checked."),
            }
            entries.append(entry)
            pending_entry = entry
            # BREAK executes before the entry is shown; no later ping is read.
            break

        if ping_ms > healthy_limit:
            lag_streak += 1
            if lag_streak >= lag_limit:
                failure_type = "lag_escalation"
                stop_reason = (f"Day {day}: {lag_limit} consecutive minor lag spikes "
                               "triggered escalation.")
                critical_days += 1
                entry = {
                    "day": day, "ping_ms": ping_ms, "status": "ESCALATED FAILURE",
                    "lag_streak": lag_streak, "action": "break", "highlight": "break",
                    "explanation": (f"This is slow day {lag_streak} in a row, reaching the "
                                    f"limit of {lag_limit}. The break statement stops the loop."),
                }
                entries.append(entry)
                pending_entry = entry
                # Repeated lag is another failure rule, so it also BREAKS.
                break
            lag_days += 1
            entry = {
                "day": day, "ping_ms": ping_ms, "status": "MINOR LAG",
                "lag_streak": lag_streak, "action": "continue", "highlight": "continue",
                "explanation": (f"{ping_ms} ms is above {healthy_limit} ms but does not exceed "
                                f"{critical_limit} ms. Slow-day streak: {lag_streak} of "
                                f"{lag_limit}. Continue skips healthy processing and moves on."),
            }
            entries.append(entry)
            pending_entry = entry
            # CONTINUE bypasses the healthy-day code below.
            continue

        lag_streak = 0
        healthy_days += 1
        entry = {
            "day": day, "ping_ms": ping_ms, "status": "HEALTHY",
            "lag_streak": 0, "action": "record", "highlight": "for",
            "explanation": (f"{ping_ms} ms is at or below {healthy_limit} ms. "
                            "Record a healthy day, reset the lag streak, and let the for loop proceed."),
        }
        entries.append(entry)
        pending_entry = entry

    # A final healthy day or a break exits the for loop before presentation.
    if pending_entry is not None:
        yield pending_entry

    report = {
        "requested_days": days, "entries": entries,
        "healthy_days": healthy_days, "lag_days": lag_days,
        "critical_days": critical_days,
        "stopped_early": critical_days > 0 and len(entries) < days,
        "scenario": scenario,
        "reading_source": "fixed demo" if ping_values is not None else "random",
        "seed": seed, "stop_reason": stop_reason, "failure_type": failure_type,
        "healthy_limit": healthy_limit, "critical_limit": critical_limit,
        "lag_limit": lag_limit,
    }
    report.update(report_statistics(report))
    return report


def monitor_server(days=7, seed=None, ping_values=None, scenario="stable",
                   healthy_limit=HEALTHY_LIMIT, critical_limit=CRITICAL_LIMIT,
                   lag_limit=LAG_LIMIT):
    """Run the same lazy simulation to completion for the terminal or tests."""
    simulation = iter_monitor(days, seed, ping_values, scenario,
                              healthy_limit, critical_limit, lag_limit)
    while True:
        try:
            next(simulation)
        except StopIteration as finished:
            return finished.value


def _entry_action(entry):
    """Recover the action for older history files that did not store it."""
    if "action" in entry:
        return entry["action"]
    if entry["status"] == "MINOR LAG":
        return "continue"
    if entry["status"] in ("CRITICAL FAILURE", "ESCALATED FAILURE"):
        return "break"
    return "record"


def report_statistics(report):
    """Calculate statistics only from days that were actually checked."""
    entries = report.get("entries", [])
    checked = len(entries)
    pings = [entry["ping_ms"] for entry in entries]
    longest = 0
    streak = 0
    for entry in entries:
        if entry["status"] in ("MINOR LAG", "ESCALATED FAILURE"):
            streak += 1
        else:
            streak = 0
        longest = max(longest, entry.get("lag_streak", streak))
    healthy = sum(entry["status"] == "HEALTHY" for entry in entries)
    return {
        "checked_days": checked,
        "average_ping_ms": sum(pings) / checked if checked else None,
        "highest_ping_ms": max(pings) if pings else None,
        "max_lag_streak": longest,
        "healthy_rate": healthy / checked * 100 if checked else 0,
    }


def _report_counts(report):
    entries = report.get("entries", [])
    return (
        sum(entry["status"] == "HEALTHY" for entry in entries),
        sum(entry["status"] == "MINOR LAG" for entry in entries),
        sum(_entry_action(entry) == "break" for entry in entries),
    )


def format_report(report):
    """Format new or legacy history records as a readable text report."""
    healthy_limit = report.get("healthy_limit", HEALTHY_LIMIT)
    critical_limit = report.get("critical_limit", CRITICAL_LIMIT)
    lag_limit = report.get("lag_limit", LAG_LIMIT)
    stats = report_statistics(report)
    healthy, lag, failures = _report_counts(report)
    scenario = report.get("scenario", "stable")
    scenario_name = SCENARIOS.get(scenario, {}).get("name", str(scenario))
    average = f"{stats['average_ping_ms']:.2f} ms" if stats["checked_days"] else "N/A"
    highest = f"{stats['highest_ping_ms']} ms" if stats["checked_days"] else "N/A"
    lines = [
        "SERVER UPTIME MONITORING LOG",
        "=" * 68,
        "Simulation only: one generated ping per day; no real server contacted.",
        f"Scenario: {scenario_name} | Readings: {report.get('reading_source', 'random')}",
        f"Healthy: 0-{healthy_limit} ms | Minor lag: {healthy_limit + 1}-{critical_limit} ms | Critical: above {critical_limit} ms",
        f"Extra failure rule: {lag_limit} consecutive lag spikes trigger escalation.",
        "-" * 68,
    ]
    streak = 0
    for entry in report.get("entries", []):
        action = _entry_action(entry)
        if action == "continue":
            action_text = "continue: skip healthy processing"
        elif action == "break":
            action_text = "break: stop monitoring"
        else:
            action_text = "server healthy"
        streak = streak + 1 if entry["status"] in ("MINOR LAG", "ESCALATED FAILURE") else 0
        lines.append(
            f"Day {entry['day']:03d} | {entry['ping_ms']:3d} ms | "
            f"{entry['status']:<17} | {action_text} | lag streak: {entry.get('lag_streak', streak)}"
        )

    requested = report.get("requested_days", stats["checked_days"])
    lines.extend([
        "-" * 68,
        "SUMMARY",
        f"Requested days       : {requested}",
        f"Days checked         : {stats['checked_days']}",
        f"Healthy days         : {healthy}",
        f"Minor lag days       : {lag}",
        f"Failures             : {failures}",
        f"Days not evaluated   : {requested - stats['checked_days']}",
        f"Healthy check rate   : {stats['healthy_rate']:.2f}%",
        f"Average ping         : {average}",
        f"Highest ping         : {highest}",
        f"Longest lag streak   : {stats['max_lag_streak']}",
        "Healthy check rate = healthy days / checked days x 100.",
        "",
        "CHECK DISTRIBUTION (# is approximately one check; capped at 25)",
    ])
    for name, count in [("Healthy", healthy), ("Minor lag", lag), ("Failure", failures)]:
        lines.append(f"{name:<10} {'#' * min(count, 25):<25} {count}")
    lines.append(f"Stop reason: {report.get('stop_reason', 'No stop reason recorded.')}")
    lines.append("This sample-based simulation does not measure real server uptime.")
    return "\n".join(lines)


def comparison_rows(first, second):
    """Return display-ready metric triples for a side-by-side comparison."""
    def values(report):
        stats = report_statistics(report)
        healthy, lag, failures = _report_counts(report)
        entries = report.get("entries", [])
        scenario = report.get("scenario", "stable")
        failed = bool(entries and _entry_action(entries[-1]) == "break")
        return [
            ("Saved at", str(report.get("created_at", "Not saved"))),
            ("Scenario", SCENARIOS.get(scenario, {}).get("name", str(scenario))),
            ("Readings", str(report.get("reading_source", "random"))),
            ("Seed", "Random each run" if report.get("seed") is None else str(report["seed"])),
            ("Requested days", str(report.get("requested_days", stats["checked_days"]))),
            ("Checked days", str(stats["checked_days"])),
            ("Healthy days", str(healthy)),
            ("Minor lag days", str(lag)),
            ("Failures", str(failures)),
            ("Healthy check rate", f"{stats['healthy_rate']:.2f}%"),
            ("Average ping", f"{stats['average_ping_ms']:.2f} ms" if stats["checked_days"] else "N/A"),
            ("Highest ping", f"{stats['highest_ping_ms']} ms" if stats["checked_days"] else "N/A"),
            ("Longest lag streak", str(stats["max_lag_streak"])),
            ("Healthy limit", f"{report.get('healthy_limit', HEALTHY_LIMIT)} ms"),
            ("Critical limit", f"{report.get('critical_limit', CRITICAL_LIMIT)} ms"),
            ("Lag limit", f"{report.get('lag_limit', LAG_LIMIT)} consecutive days"),
            ("Stopped on day", str(entries[-1]["day"]) if failed else "Completed" if entries else "Not started"),
            ("Stop reason", str(report.get("stop_reason", "No stop reason recorded."))),
        ]
    return [(left[0], left[1], right[1]) for left, right in zip(values(first), values(second))]


def export_csv(report, path):
    """Export processed daily readings and their rules as a UTF-8 CSV file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["day", "ping_ms", "status", "lag_streak", "action",
              "healthy_limit", "critical_limit", "lag_limit"]
    streak = 0
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for entry in report.get("entries", []):
            streak = streak + 1 if entry["status"] in ("MINOR LAG", "ESCALATED FAILURE") else 0
            writer.writerow({
                "day": entry["day"], "ping_ms": entry["ping_ms"],
                "status": entry["status"], "lag_streak": entry.get("lag_streak", streak),
                "action": _entry_action(entry),
                "healthy_limit": report.get("healthy_limit", HEALTHY_LIMIT),
                "critical_limit": report.get("critical_limit", CRITICAL_LIMIT),
                "lag_limit": report.get("lag_limit", LAG_LIMIT),
            })


def save_run_history(report, directory="logs/history"):
    """Save a separate JSON record and text log with settings and statistics."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone()
    run_id = timestamp.strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid4().hex[:8]
    record = {**report, "run_id": run_id, "created_at": timestamp.isoformat()}
    record.setdefault("healthy_limit", HEALTHY_LIMIT)
    record.setdefault("critical_limit", CRITICAL_LIMIT)
    record.setdefault("lag_limit", LAG_LIMIT)
    record.update(report_statistics(record))
    text_path = directory / f"{run_id}.txt"
    json_path = directory / f"{run_id}.json"
    text_path.write_text(format_report(record) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return json_path


def positive_integer(value):
    """Validate a positive command-line integer."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main():
    parser = argparse.ArgumentParser(
        description="Simulate daily server ping statuses using for, continue and break."
    )
    parser.add_argument("--days", type=positive_integer, default=7,
                        help="number of simulated days (default: 7)")
    parser.add_argument("--seed", type=int, help="seed for repeatable random results")
    parser.add_argument("--scenario", choices=SCENARIOS, default="stable",
                        help="random network scenario (default: stable)")
    parser.add_argument("--healthy-limit", type=int, default=HEALTHY_LIMIT,
                        help="largest healthy ping in ms (default: 100)")
    parser.add_argument("--critical-limit", type=positive_integer, default=CRITICAL_LIMIT,
                        help="pings above this value fail immediately (default: 300)")
    parser.add_argument("--lag-limit", type=positive_integer, default=LAG_LIMIT,
                        help="consecutive lag readings that cause failure (default: 3)")
    demos = parser.add_mutually_exclusive_group()
    demos.add_argument("--demo", action="store_true",
                       help="use fixed readings to demonstrate all three statuses")
    demos.add_argument("--demo-lag", action="store_true",
                       help="demonstrate failure after consecutive lag spikes")
    parser.add_argument("--history-dir", type=Path, default=Path("logs/history"),
                        help="directory for separate timestamped run records")
    parser.add_argument("--log-file", type=Path, default=Path("logs/server_uptime.log"),
                        help="text log destination (default: logs/server_uptime.log)")
    parser.add_argument("--csv-file", type=Path, help="also export the daily readings as CSV")
    args = parser.parse_args()

    is_demo = args.demo or args.demo_lag
    if is_demo and args.days > len(DEMO_PINGS):
        parser.error("demo modes support at most 7 days")
    if is_demo and args.seed is not None:
        parser.error("--seed is for random mode; use it without a demo")
    try:
        report = monitor_server(
            days=args.days, seed=args.seed,
            ping_values=DEMO_PINGS if args.demo else LAG_DEMO_PINGS if args.demo_lag else None,
            scenario="unstable" if args.demo else "busy" if args.demo_lag else args.scenario,
            healthy_limit=args.healthy_limit, critical_limit=args.critical_limit,
            lag_limit=args.lag_limit,
        )
    except ValueError as error:
        parser.error(str(error))
    output = format_report(report)
    try:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        args.log_file.write_text(output + "\n", encoding="utf-8")
        save_run_history(report, args.history_dir)
        if args.csv_file is not None:
            export_csv(report, args.csv_file)
    except OSError as error:
        parser.error(f"could not save the log, run history or CSV: {error}")

    print(output)
    print(f"\nLog saved to: {args.log_file}")
    if args.csv_file is not None:
        print(f"CSV saved to: {args.csv_file}")


if __name__ == "__main__":
    main()
