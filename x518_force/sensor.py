"""Bounded synchronous acquisition; no GUI, console keys or device writes."""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import struct
import threading
import time

import serial

from .protocol import append_crc, build_read_request, parse_measurement_response
from .transport import read_response


class SensorError(RuntimeError):
    """Serial transport failed or sensor is not open; no sample is returned."""


@dataclass(frozen=True)
class Config:
    port: str = ""
    baud: int = 115200
    slave: int = 1
    parity: str = "N"
    stopbits: int = 1
    timeout: float = 1.0
    decimals: int = 2
    unit: str = "kg"
    word_swap: bool = False

    def __post_init__(self):
        for name, allowed in (
            ("baud", (2400, 4800, 9600, 19200, 38400, 57600, 115200)),
            ("slave", range(1, 248)), ("stopbits", (1, 2)),
            ("decimals", range(6)),
        ):
            value = getattr(self, name)
            if type(value) is not int or value not in allowed:
                raise ValueError(f"invalid {name}: {value!r}")
        if not isinstance(self.port, str):
            raise ValueError("port must be a string")
        if self.parity not in ("N", "E", "O"):
            raise ValueError("parity must be N, E or O")
        if self.unit not in ("t", "kg", "g", "kN", "N", "lb"):
            raise ValueError("invalid unit label")
        if (isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float))
                or not math.isfinite(self.timeout) or not 0.05 <= self.timeout <= 10):
            raise ValueError("timeout must be finite and 0.05..10 seconds")
        if type(self.word_swap) is not bool:
            raise ValueError("word_swap must be bool")


@dataclass(frozen=True)
class Sample:
    raw: tuple[int, int]
    values: tuple[float, float]
    unit: str
    decimals: int
    timestamp: str
    monotonic_s: float
    request_started_s: float
    source: str
    tx: bytes
    rx: bytes

    def age_s(self) -> float:
        """Host time since reception; not device sample age."""
        return time.monotonic() - self.monotonic_s


def list_ports():
    """Return pyserial port descriptors without opening or probing devices."""
    from serial.tools.list_ports import comports
    return sorted(comports(), key=lambda item: item.device)


class _DemoPort:
    """Deterministic synthetic frames, using the real reception/parser path."""

    def __init__(self, config):
        self.config = config
        self.timeout = config.timeout
        self.buffer = bytearray()
        self.index = 0

    @property
    def in_waiting(self):
        return len(self.buffer)

    def reset_input_buffer(self):
        self.buffer.clear()

    def write(self, request):
        self.index += 1
        payload = b""
        for value in (100 + self.index, -50 - self.index):
            data = struct.pack(">i", value)
            payload += data[2:] + data[:2] if self.config.word_swap else data
        self.buffer.extend(append_crc(bytes([self.config.slave, 3, 8]) + payload))
        return len(request)

    def read(self, size):
        size = min(size, 2, len(self.buffer))
        data = bytes(self.buffer[:size])
        del self.buffer[:size]
        return data

    def close(self):
        self.buffer.clear()


class X518Sensor:
    """One serial owner. read() returns a fresh pair or raises an exception.

    Constructing is side-effect free; open explicitly or use a with statement.
    Reads and close are serialized. This interface is not a real-time scheduler.
    """

    def __init__(self, config: Config, *, demo: bool = False):
        if type(demo) is not bool:
            raise ValueError("demo must be bool")
        if not demo and not config.port.strip():
            raise ValueError("a hardware port is required")
        self.config = config
        self.demo = demo
        self._port = None
        self._lock = threading.Lock()

    def open(self):
        with self._lock:
            if self._port is not None:
                return self
            if self.demo:
                self._port = _DemoPort(self.config)
            else:
                try:
                    self._port = serial.Serial(
                        port=self.config.port, baudrate=self.config.baud, bytesize=8,
                        parity=self.config.parity, stopbits=self.config.stopbits,
                        timeout=self.config.timeout, write_timeout=self.config.timeout,
                    )
                except (serial.SerialException, OSError) as exc:
                    raise SensorError(f"cannot open {self.config.port}: {exc}") from exc
        return self

    def read(self) -> Sample:
        """Block for one transaction; no retries, cached data or zero fallback."""
        with self._lock:
            if self._port is None:
                raise SensorError("sensor is closed; use with X518Sensor(...) or open()")
            config = self.config
            tx = build_read_request(config.slave)
            started = time.monotonic()
            bits = 1 + 8 + (config.parity != "N") + config.stopbits
            gap = 0.002 if config.baud > 19200 else 3.5 * bits / config.baud
            try:
                self._port.reset_input_buffer()
                time.sleep(gap)
                written = self._port.write(tx)
                if written != len(tx):
                    raise SensorError(f"short serial write: {written}/{len(tx)}")
                rx = read_response(self._port, config.timeout)
            except (serial.SerialException, OSError) as exc:
                raise SensorError(f"serial transaction failed: {exc}") from exc
            raw = parse_measurement_response(rx, config.slave, config.word_swap)
            received = time.monotonic()
            return Sample(
                raw=raw, values=tuple(value / 10 ** config.decimals for value in raw),
                unit=config.unit, decimals=config.decimals,
                timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                monotonic_s=received, request_started_s=started,
                source="demo" if self.demo else "serial", tx=tx, rx=rx,
            )

    def close(self):
        with self._lock:
            if self._port is not None:
                port, self._port = self._port, None
                try:
                    port.close()
                except (serial.SerialException, OSError) as exc:
                    raise SensorError(f"cannot close serial port: {exc}") from exc

    def __enter__(self):
        return self.open()

    def __exit__(self, *unused):
        self.close()
