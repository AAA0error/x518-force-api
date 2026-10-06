"""Measure real API throughput; only FC03 reads, no per-sample console output."""

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import time

from x518_force import Config, ProtocolError, SensorError, X518Sensor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--hz", type=float, default=1000)
    stop = parser.add_mutually_exclusive_group()
    stop.add_argument("--duration", type=float, help="stop after this many seconds (default: 10)")
    stop.add_argument("--count", type=int, help="stop after this many attempts; no duration limit")
    parser.add_argument("--unpaced", action="store_true", help="start the next read immediately; ignore hz")
    parser.add_argument("--timeout", type=float, default=0.2)
    parser.add_argument("--output-dir", type=Path, default=Path("dist/benchmarks"))
    args = parser.parse_args()
    if args.duration is None and args.count is None:
        args.duration = 10
    if (not math.isfinite(args.hz) or args.hz <= 0 or
            (args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0))):
        parser.error("hz and duration must be positive and finite")
    if args.count is not None and args.count <= 0:
        parser.error("count must be positive")
    config = Config(port=args.port, timeout=args.timeout)
    rows = []
    consecutive_errors = 0
    with X518Sensor(config) as sensor:
        started = time.perf_counter()
        deadline = started + args.duration if args.duration is not None else None
        while ((deadline is None or time.perf_counter() < deadline) and
               (args.count is None or len(rows) < args.count)):
            before = time.perf_counter()
            row = {"attempt": len(rows) + 1, "status": "ok", "error": ""}
            try:
                sample = sensor.read()
                row.update(ch1_raw=sample.raw[0], ch2_raw=sample.raw[1],
                           ch1_scaled=sample.values[0], ch2_scaled=sample.values[1],
                           unit=sample.unit, timestamp=sample.timestamp,
                           tx_hex=sample.tx.hex(" "), rx_hex=sample.rx.hex(" "))
                consecutive_errors = 0
            except (ProtocolError, SensorError) as exc:
                row.update(status=type(exc).__name__, error=str(exc))
                consecutive_errors += 1
            after = time.perf_counter()
            row.update(completed_s=after - started, read_ms=(after - before) * 1000)
            rows.append(row)
            if consecutive_errors >= 5 or row["status"] == "SensorError":
                break
            if not args.unpaced and (args.count is None or len(rows) < args.count):
                remaining = 1 / args.hz - (after - before)
                if deadline is not None:
                    remaining = min(remaining, deadline - after)
                if remaining > 0:
                    time.sleep(remaining)
        elapsed = time.perf_counter() - started

    valid = [row for row in rows if row["status"] == "ok"]
    intervals = [(b["completed_s"] - a["completed_s"]) * 1000
                 for a, b in zip(valid, valid[1:])]
    latencies = sorted(row["read_ms"] for row in valid)
    summary = {
        "target_hz": None if args.unpaced else args.hz,
        "requested_duration_s": args.duration, "requested_count": args.count,
        "unpaced": args.unpaced,
        "elapsed_s": elapsed, "attempts": len(rows), "successful_reads": len(valid),
        "errors": len(rows) - len(valid), "effective_hz": len(valid) / elapsed,
        "completion_interval_mean_ms": statistics.mean(intervals) if intervals else None,
        "read_mean_ms": statistics.mean(latencies) if latencies else None,
        "read_p95_ms": latencies[math.ceil(len(latencies) * 0.95) - 1] if latencies else None,
        "read_min_ms": min(latencies) if latencies else None,
        "read_max_ms": max(latencies) if latencies else None,
        "host_config": {"port": config.port, "baud": config.baud, "slave": config.slave,
                        "timeout_s": config.timeout, "decimals": config.decimals,
                        "unit_label": config.unit},
        "note": "Successful Modbus reads per second, not independently verified device sampling rate.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    label = "unpaced" if args.unpaced else f"{args.hz:g}hz"
    base = args.output_dir / f"rate_{label}_{stamp}"
    csv_path = base.with_suffix(".csv")
    fields = ["attempt", "status", "error", "completed_s", "read_ms", "timestamp",
              "ch1_raw", "ch2_raw", "ch1_scaled", "ch2_scaled", "unit", "tx_hex", "rx_hex"]
    with csv_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary["csv_path"] = str(csv_path.resolve())
    with base.with_suffix(".json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps(summary, indent=2))
    return int(summary["errors"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
