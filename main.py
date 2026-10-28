"""Server Uptime Monitoring Log: a Python loop and random-number simulation."""

import argparse
import random
from pathlib import Path


DEMO_PINGS = [45, 160, 72, 100, 300, 301, 55]
HEALTHY_LIMIT = 100
CRITICAL_LIMIT = 300


def monitor_server(days=7, seed=None, ping_values=None):
    """Simulate one ping per day and return the log and summary counters.

    Optional ping_values make classroom demonstrations and tests repeatable.
    A local random generator keeps seeded runs independent of other code.
    """
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("days must be a positive integer")

    rng = random.Random(seed)
    readings = iter(ping_values) if ping_values is not None else None
    entries = []
    healthy_days = 0
    lag_days = 0
    critical_days = 0

    # FOR visits each simulated day. No real time delay or network is needed.
    for day in range(1, days + 1):
        if readings is None:
            ping_ms = rng.randint(20, 350)
        else:
            try:
                ping_ms = next(readings)
            except StopIteration as error:
                raise ValueError("Not enough ping values for the requested days") from error

        if isinstance(ping_ms, bool) or not isinstance(ping_ms, int) or ping_ms < 0:
            raise ValueError("Each ping must be a non-negative integer in milliseconds")

        if ping_ms > CRITICAL_LIMIT:
            entries.append({"day": day, "ping_ms": ping_ms, "status": "CRITICAL FAILURE"})
            critical_days += 1
            # BREAK exits the loop immediately; later days are never evaluated.
            break

        if ping_ms > HEALTHY_LIMIT:
            entries.append({"day": day, "ping_ms": ping_ms, "status": "MINOR LAG"})
            lag_days += 1
            # CONTINUE skips the healthy-day code and proceeds to the next day.
            continue

        entries.append({"day": day, "ping_ms": ping_ms, "status": "HEALTHY"})
        healthy_days += 1

    return {
        "requested_days": days,
        "entries": entries,
        "healthy_days": healthy_days,
        "lag_days": lag_days,
        "critical_days": critical_days,
        "stopped_early": critical_days > 0 and len(entries) < days,
    }


def format_report(report):
    """Turn the simulation result into the terminal and saved text log."""
    lines = [
        "SERVER UPTIME MONITORING LOG",
        "=" * 68,
        "Simulation only: one generated ping per day; no real server contacted.",
        "Healthy: 0-100 ms | Minor lag: 101-300 ms | Critical: above 300 ms",
        "-" * 68,
    ]

    for entry in report["entries"]:
        if entry["status"] == "MINOR LAG":
            action = "continue: skip healthy processing"
        elif entry["status"] == "CRITICAL FAILURE":
            action = "break: stop monitoring"
        else:
            action = "server healthy"
        lines.append(
            f"Day {entry['day']:03d} | {entry['ping_ms']:3d} ms | "
            f"{entry['status']:<16} | {action}"
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
        f"Critical failures    : {report['critical_days']}",
        f"Days not evaluated   : {report['requested_days'] - checked}",
        f"Healthy check rate   : {healthy_rate:.2f}%",
        "Healthy check rate = healthy days / checked days x 100.",
    ])
    if report["critical_days"]:
        lines.append("Monitoring halted on a critical failure.")
    else:
        lines.append("Monitoring completed all requested days.")
    lines.append("This sample-based simulation does not measure real server uptime.")
    return "\n".join(lines)


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
    parser.add_argument("--demo", action="store_true",
                        help="use fixed readings to demonstrate all three statuses")
    parser.add_argument("--log-file", type=Path, default=Path("logs/server_uptime.log"),
                        help="text log destination (default: logs/server_uptime.log)")
    args = parser.parse_args()

    if args.demo and args.days > len(DEMO_PINGS):
        parser.error("--demo supports at most 7 days")
    if args.demo and args.seed is not None:
        parser.error("--seed is for random mode; use it without --demo")

    report = monitor_server(
        days=args.days,
        seed=args.seed,
        ping_values=DEMO_PINGS if args.demo else None,
    )
    output = format_report(report)
    try:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        args.log_file.write_text(output + "\n", encoding="utf-8")
    except OSError as error:
        parser.error(f"could not save log to {args.log_file}: {error}")

    print(output)
    print(f"\nLog saved to: {args.log_file}")


if __name__ == "__main__":
    main()
