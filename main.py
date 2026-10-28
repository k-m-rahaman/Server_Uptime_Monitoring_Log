"""Server Uptime Monitoring Log: a Python loop and random-number simulation."""

import argparse
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


def monitor_server(days=7, seed=None, ping_values=None, scenario="stable"):
    """Simulate one ping per day and return the log and summary counters.

    Optional ping_values make classroom demonstrations and tests repeatable.
    A local random generator keeps seeded runs independent of other code.
    """
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("days must be a positive integer")
    if scenario not in SCENARIOS:
        raise ValueError("scenario must be stable, busy or unstable")

    rng = random.Random(seed)
    readings = iter(ping_values) if ping_values is not None else None
    entries = []
    healthy_days = 0
    lag_days = 0
    critical_days = 0
    lag_streak = 0
    max_lag_streak = 0
    stop_reason = "All requested days were checked."
    failure_type = None

    # FOR visits each simulated day. No real time delay or network is needed.
    for day in range(1, days + 1):
        if readings is None:
            ping_ms = rng.randint(*SCENARIOS[scenario]["range"])
        else:
            try:
                ping_ms = next(readings)
            except StopIteration as error:
                raise ValueError("Not enough ping values for the requested days") from error

        if isinstance(ping_ms, bool) or not isinstance(ping_ms, int) or ping_ms < 0:
            raise ValueError("Each ping must be a non-negative integer in milliseconds")

        if ping_ms > CRITICAL_LIMIT:
            entries.append({"day": day, "ping_ms": ping_ms,
                            "status": "CRITICAL FAILURE", "lag_streak": 0,
                            "action": "break"})
            critical_days += 1
            stop_reason = f"Day {day}: ping {ping_ms} ms exceeded the 300 ms critical threshold."
            failure_type = "critical_ping"
            # BREAK exits the loop immediately; later days are never evaluated.
            break

        if ping_ms > HEALTHY_LIMIT:
            lag_streak += 1
            max_lag_streak = max(max_lag_streak, lag_streak)
            if lag_streak >= LAG_LIMIT:
                entries.append({"day": day, "ping_ms": ping_ms,
                                "status": "ESCALATED FAILURE", "lag_streak": lag_streak,
                                "action": "break"})
                critical_days += 1
                failure_type = "lag_escalation"
                stop_reason = f"Day {day}: {LAG_LIMIT} consecutive minor lag spikes triggered escalation."
                # Repeated lag is an additional failure rule, so it also BREAKS.
                break
            entries.append({"day": day, "ping_ms": ping_ms, "status": "MINOR LAG",
                            "lag_streak": lag_streak, "action": "continue"})
            lag_days += 1
            # CONTINUE skips the healthy-day code and proceeds to the next day.
            continue

        lag_streak = 0  # A healthy day breaks a sequence of lag spikes.
        entries.append({"day": day, "ping_ms": ping_ms, "status": "HEALTHY",
                        "lag_streak": 0, "action": "record"})
        healthy_days += 1

    return {
        "requested_days": days,
        "entries": entries,
        "healthy_days": healthy_days,
        "lag_days": lag_days,
        "critical_days": critical_days,
        "stopped_early": critical_days > 0 and len(entries) < days,
        "scenario": scenario,
        "reading_source": "fixed demo" if ping_values is not None else "random",
        "seed": seed,
        "stop_reason": stop_reason,
        "failure_type": failure_type,
        "max_lag_streak": max_lag_streak,
    }


def format_report(report):
    """Turn the simulation result into the terminal and saved text log."""
    lines = [
        "SERVER UPTIME MONITORING LOG",
        "=" * 68,
        "Simulation only: one generated ping per day; no real server contacted.",
        f"Scenario: {SCENARIOS[report['scenario']]['name']} | Readings: {report['reading_source']}",
        "Healthy: 0-100 ms | Minor lag: 101-300 ms | Critical: above 300 ms",
        "Extra failure rule: 3 consecutive lag spikes trigger escalation.",
        "-" * 68,
    ]

    for entry in report["entries"]:
        if entry["status"] == "MINOR LAG":
            action = "continue: skip healthy processing"
        elif entry["action"] == "break":
            action = "break: stop monitoring"
        else:
            action = "server healthy"
        lines.append(
            f"Day {entry['day']:03d} | {entry['ping_ms']:3d} ms | "
            f"{entry['status']:<17} | {action} | lag streak: {entry['lag_streak']}"
        )

    checked = len(report["entries"])
    healthy_rate = report["healthy_days"] / checked * 100
    lines.extend([
        "-" * 68,
        "SUMMARY",
        f"Requested days       : {report['requested_days']}",
        f"Days checked         : {checked}",
        f"Healthy days         : {report['healthy_days']}",
        f"Minor lag days       : {report['lag_days']}",
        f"Failures             : {report['critical_days']}",
        f"Days not evaluated   : {report['requested_days'] - checked}",
        f"Healthy check rate   : {healthy_rate:.2f}%",
        f"Longest lag streak   : {report['max_lag_streak']}",
        "Healthy check rate = healthy days / checked days x 100.",
        "",
        "CHECK DISTRIBUTION (# is approximately one check; capped at 25)",
    ])
    for label, count in [("Healthy", report["healthy_days"]),
                         ("Minor lag", report["lag_days"]),
                         ("Failure", report["critical_days"])]:
        lines.append(f"{label:<10} {'#' * min(count, 25):<25} {count}")
    lines.append(f"Stop reason: {report['stop_reason']}")
    lines.append("This sample-based simulation does not measure real server uptime.")
    return "\n".join(lines)


def save_run_history(report, directory="logs/history"):
    """Save a separate JSON record and text log for every simulation."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone()
    run_id = timestamp.strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid4().hex[:8]
    record = {**report, "run_id": run_id, "created_at": timestamp.isoformat()}
    text_path = directory / f"{run_id}.txt"
    json_path = directory / f"{run_id}.json"
    text_path.write_text(format_report(report) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return json_path


def positive_integer(value):
    """Validate the --days command-line argument."""
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
    parser.add_argument("--seed", type=int,
                        help="seed for repeatable random results")
    parser.add_argument("--scenario", choices=SCENARIOS, default="stable",
                        help="random network scenario (default: stable)")
    demos = parser.add_mutually_exclusive_group()
    demos.add_argument("--demo", action="store_true",
                        help="use fixed readings to demonstrate all three statuses")
    demos.add_argument("--demo-lag", action="store_true",
                       help="demonstrate failure after three consecutive lag spikes")
    parser.add_argument("--history-dir", type=Path, default=Path("logs/history"),
                        help="directory for separate timestamped run records")
    parser.add_argument("--log-file", type=Path, default=Path("logs/server_uptime.log"),
                        help="text log destination (default: logs/server_uptime.log)")
    args = parser.parse_args()

    is_demo = args.demo or args.demo_lag
    if is_demo and args.days > len(DEMO_PINGS):
        parser.error("demo modes support at most 7 days")
    if is_demo and args.seed is not None:
        parser.error("--seed is for random mode; use it without a demo")

    report = monitor_server(
        days=args.days,
        seed=args.seed,
        ping_values=DEMO_PINGS if args.demo else LAG_DEMO_PINGS if args.demo_lag else None,
        scenario="unstable" if args.demo else "busy" if args.demo_lag else args.scenario,
    )
    output = format_report(report)
    try:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        args.log_file.write_text(output + "\n", encoding="utf-8")
        save_run_history(report, args.history_dir)
    except OSError as error:
        parser.error(f"could not save the log or run history: {error}")

    print(output)
    print(f"\nLog saved to: {args.log_file}")


if __name__ == "__main__":
    main()
