"""Time-controlled fragmented reception and timeout regression tests."""

import unittest
from unittest.mock import patch

from x518_force.transport import read_response

FRAME = bytes.fromhex("01 03 08 00 00 00 06 FF FF 67 4B 77 F4")


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class ScheduledPort:
    def __init__(self, clock, arrivals):
        self.clock = clock
        self.arrivals = list(arrivals)
        self.buffer = bytearray()

    @property
    def timeout(self):
        return 0

    @timeout.setter
    def timeout(self, value):
        raise AssertionError("receiver must not reconfigure serial timeout")

    @property
    def in_waiting(self):
        while self.arrivals and self.arrivals[0][0] <= self.clock.now:
            self.buffer.extend(self.arrivals.pop(0)[1])
        return len(self.buffer)

    def read(self, size):
        if size > len(self.buffer):
            raise AssertionError("receiver must only request buffered bytes")
        data = bytes(self.buffer[:size])
        del self.buffer[:size]
        return data


class TransportTests(unittest.TestCase):
    def receive(self, arrivals, timeout=0.05):
        clock = Clock()
        port = ScheduledPort(clock, arrivals)
        with patch("x518_force.transport.time.monotonic", clock.monotonic), \
                patch("x518_force.transport.time.sleep", clock.sleep):
            result = read_response(port, timeout)
        return result, clock.now

    def test_delayed_fragments_without_driver_reconfiguration(self):
        result, elapsed = self.receive([(0.002, FRAME[:2]), (0.006, FRAME[2:7]),
                                        (0.01, FRAME[7:])])
        self.assertEqual(result, FRAME)
        self.assertLess(elapsed, 0.011)

    def test_empty_and_partial_responses_share_one_deadline(self):
        for arrivals, expected in [([], b""), ([(0.02, FRAME[:3]), (0.06, FRAME[3:])], FRAME[:3])]:
            with self.subTest(arrivals=arrivals):
                result, elapsed = self.receive(arrivals)
                self.assertEqual(result, expected)
                self.assertAlmostEqual(elapsed, 0.05)

    def test_short_exception_does_not_wait_for_thirteen_bytes(self):
        exception = bytes.fromhex("01 83 02 C0 F1")
        result, elapsed = self.receive([(0.001, exception[:3]), (0.003, exception[3:])])
        self.assertEqual(result, exception)
        self.assertLess(elapsed, 0.004)

    def test_invalid_header_and_buffered_extra_bytes_are_preserved(self):
        invalid = b"\x01\x04\x08"
        for frame in (invalid, FRAME + b"\xff"):
            with self.subTest(frame=frame):
                result, elapsed = self.receive([(0, frame)])
                self.assertEqual(result, frame)
                self.assertEqual(elapsed, 0)


if __name__ == "__main__":
    unittest.main()
