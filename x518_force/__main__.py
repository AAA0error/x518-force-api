"""Portable command-line smoke test for the public interface."""

import argparse
from dataclasses import asdict
import json
import math
import sys
import time

from . import Config, ProtocolError, SensorError, X518Sensor, list_ports


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only X518 Python API")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--port", default="")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--slave", type=int, default=1)
    parser.add_argument("--parity", choices=("N", "E", "O"), default="N")
    parser.add_argument("--stopbits", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=1)
    parser.add_argument("--decimals", type=int, default=2)
    parser.add_argument("--unit", default="kg")
    parser.add_argument("--word-swap", action="store_true")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=0.2)
    args = parser.parse_args(argv)
    if args.list_ports:
        for port in list_ports():
            print(f"{port.device}: {port.description} [{port.hwid}]")
        return 0
    if args.count <= 0 or not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("count and interval must be positive and finite")
    try:
        config = Config(port=args.port, baud=args.baud, slave=args.slave,
                        parity=args.parity, stopbits=args.stopbits,
                        timeout=args.timeout, decimals=args.decimals,
                        unit=args.unit, word_swap=args.word_swap)
        with X518Sensor(config, demo=args.demo) as sensor:
            for index in range(args.count):
                started = time.monotonic()
                sample = asdict(sensor.read())
                sample["tx"] = sample["tx"].hex(" ")
                sample["rx"] = sample["rx"].hex(" ")
                print(json.dumps(sample), flush=True)
                if index + 1 < args.count:
                    time.sleep(max(0, args.interval - (time.monotonic() - started)))
    except (ValueError, ProtocolError, SensorError) as exc:
        print(f"X518 error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
