"""Fragmented serial reception, extracted unchanged from the original reader."""

import time


def read_response(port, timeout):
    """Accumulate fragmented reads within ONE deadline, including exception frames."""
    deadline = time.monotonic() + timeout
    original_timeout = port.timeout
    frame = bytearray()
    target = 3
    try:
        while len(frame) < target:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            port.timeout = remaining
            chunk = port.read(target - len(frame))
            if not chunk:
                break
            frame.extend(chunk)
            if len(frame) >= 3 and target == 3:
                if frame[1] == 0x83:
                    target = 5
                elif frame[1] == 3 and frame[2] == 8:
                    target = 13
                else:
                    # Invalid header: return it for strict rejection, not decoding.
                    break
        # Already-buffered extra bytes must not be silently accepted as a valid frame.
        waiting = port.in_waiting
        if waiting:
            port.timeout = 0
            frame.extend(port.read(min(waiting, 256)))
        return bytes(frame)
    finally:
        port.timeout = original_timeout
