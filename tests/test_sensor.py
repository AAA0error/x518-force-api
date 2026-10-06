import contextlib
import io
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

import serial

from x518_force import Config, ProtocolError, SensorError, X518Sensor
from x518_force.__main__ import main
from x518_force.protocol import append_crc, build_read_request, crc16, ModbusException

RESPONSE = bytes.fromhex("01 03 08 00 00 00 06 FF FF 67 4B 77 F4")


class FakePort:
    def __init__(self, response=RESPONSE, short_write=False):
        self.response = response
        self.timeout = 1.0
        self.buffer = bytearray()
        self.requests = []
        self.closed = False
        self.short_write = short_write

    @property
    def in_waiting(self):
        return len(self.buffer)

    def reset_input_buffer(self):
        self.buffer.clear()

    def write(self, request):
        self.requests.append(request)
        self.buffer.extend(self.response)
        return len(request) - int(self.short_write)

    def read(self, size):
        size = min(size, 2, len(self.buffer))
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result

    def close(self):
        self.closed = True


class SensorTests(unittest.TestCase):
    def test_manual_frame_fragmentation_scaling_and_close(self):
        port = FakePort()
        with patch("x518_force.sensor.serial.Serial", return_value=port) as factory:
            sensor = X518Sensor(Config(port="/dev/cu.usbserial-TEST"))
            factory.assert_not_called()
            with sensor:
                sample = sensor.read()
                self.assertEqual(sample.raw, (6, -39093))
                self.assertEqual(sample.values, (0.06, -390.93))
                self.assertEqual(sample.unit, "kg")
                self.assertEqual(sample.source, "serial")
                self.assertGreaterEqual(sample.age_s(), 0)
                self.assertGreaterEqual(sample.monotonic_s, sample.request_started_s)
                self.assertTrue(sample.timestamp.endswith("+00:00"))
            self.assertEqual(port.requests, [bytes.fromhex("01 03 0a 00 00 04 47 d1")])
            self.assertEqual(port.timeout, 1.0)
            self.assertTrue(port.closed)
            factory.assert_called_once_with(port="/dev/cu.usbserial-TEST", baudrate=115200,
                bytesize=8, parity="N", stopbits=1, timeout=0, write_timeout=1.0)
        with self.assertRaises(SensorError):
            sensor.read()

    def test_crc_typo(self):
        self.assertEqual(crc16(build_read_request()), 0)
        self.assertNotEqual(crc16(bytes.fromhex("01 03 0a 00 00 04 46 d1")), 0)

    def test_failures_never_return_measurements(self):
        bad_crc = RESPONSE[:-1] + bytes([RESPONSE[-1] ^ 1])
        wrong_slave = append_crc(bytes([2]) + RESPONSE[1:-2])
        wrong_count = append_crc(RESPONSE[:2] + b"\x04" + RESPONSE[3:-2])
        wrong_function = append_crc(RESPONSE[:1] + b"\x04" + RESPONSE[2:-2])
        frames = [b"", bad_crc, wrong_slave, wrong_count, wrong_function,
                  RESPONSE + b"\x00", append_crc(b"\x01\x83\x02")]
        frames += [RESPONSE[:length] for length in range(1, 13)]
        for frame in frames:
            with self.subTest(frame=frame):
                port = FakePort(frame)
                with patch("x518_force.sensor.serial.Serial", return_value=port):
                    with self.assertRaises(ProtocolError):
                        with X518Sensor(Config(port="FAKE", timeout=0.05)) as sensor:
                            sensor.read()
                self.assertTrue(port.closed)
                self.assertEqual(port.timeout, 1.0)

    def test_exception_code_is_available(self):
        port = FakePort(append_crc(b"\x01\x83\x06"))
        with patch("x518_force.sensor.serial.Serial", return_value=port):
            with X518Sensor(Config(port="FAKE")) as sensor:
                with self.assertRaises(ModbusException) as caught:
                    sensor.read()
                self.assertEqual(caught.exception.code, 6)

    def test_int32_bounds_and_word_swap(self):
        for swap in (False, True):
            values = (-2147483648, 2147483647)
            payload = b""
            for value in values:
                data = struct.pack(">i", value)
                payload += data[2:] + data[:2] if swap else data
            port = FakePort(append_crc(b"\x01\x03\x08" + payload))
            with patch("x518_force.sensor.serial.Serial", return_value=port):
                with X518Sensor(Config(port="FAKE", word_swap=swap, decimals=0)) as sensor:
                    self.assertEqual(sensor.read().raw, values)

    def test_transport_error_and_short_write(self):
        for short in (False, True):
            port = FakePort(short_write=short)
            with patch("x518_force.sensor.serial.Serial", return_value=port):
                with self.assertRaises(SensorError):
                    with X518Sensor(Config(port="FAKE")) as sensor:
                        if not short:
                            port.read = lambda size: (_ for _ in ()).throw(serial.SerialException("unplugged"))
                        sensor.read()
            self.assertTrue(port.closed)
            self.assertEqual(port.timeout, 1.0)

    def test_open_failure(self):
        with patch("x518_force.sensor.serial.Serial", side_effect=serial.SerialException("busy")):
            with self.assertRaisesRegex(SensorError, "cannot open"):
                X518Sensor(Config(port="FAKE")).open()

    def test_demo_never_opens_hardware_and_can_reopen(self):
        for swap in (False, True):
            with patch("x518_force.sensor.serial.Serial") as factory:
                sensor = X518Sensor(Config(word_swap=swap), demo=True)
                with sensor:
                    sensor.open()
                    self.assertEqual(sensor.read().raw, (101, -51))
                    sample = sensor.read()
                    self.assertEqual(sample.raw, (102, -52))
                    self.assertEqual(sample.source, "demo")
                sensor.close()
                with sensor:
                    self.assertEqual(sensor.read().raw, (101, -51))
                factory.assert_not_called()

    def test_config_validation(self):
        for key, value in [("baud", 1), ("slave", 0), ("slave", 1.5), ("slave", True),
                           ("stopbits", 3), ("decimals", 6), ("timeout", 0),
                           ("timeout", float("nan")), ("timeout", float("inf")),
                           ("parity", "bad"), ("unit", "newton"), ("word_swap", 1)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                Config(**{key: value})
        with self.assertRaises(ValueError):
            X518Sensor(Config())

    def test_cli_error_and_demo(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 1)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--demo", "--count", "1"]), 0)
        self.assertIn('"source": "demo"', output.getvalue())

    def test_module_entrypoint(self):
        result = subprocess.run([sys.executable, "-m", "x518_force", "--demo", "--count", "1"],
                                capture_output=True, text=True, check=True)
        self.assertIn('"raw": [101, -51]', result.stdout)


if __name__ == "__main__":
    unittest.main()
