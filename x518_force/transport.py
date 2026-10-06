"""Deadline-based serial reception without per-read driver reconfiguration."""

import time


def read_response(port, timeout, expected_byte_count=8):
    """Accumulate fragmented reads within ONE deadline, including exception frames."""
    deadline = time.monotonic() + timeout
    frame = bytearray()
    target = 3
    while len(frame) < target:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        waiting = port.in_waiting
        if not waiting:
            time.sleep(min(0.0005, remaining))
            continue
        # The sensor opens in nonblocking mode. Read only buffered bytes; changing
        # pyserial timeout here reconfigures the Windows driver on every fragment.
        chunk = port.read(min(waiting, target - len(frame)))
        if not chunk:
            raise OSError("serial read returned no bytes despite buffered data")
        frame.extend(chunk)
        if len(frame) >= 3 and target == 3:
            if frame[1] == 0x83:
                target = 5
            elif frame[1] == 3 and frame[2] == expected_byte_count:
                target = 5 + expected_byte_count
            else:
                break
    # Already-buffered extra bytes must not be accepted as a valid frame.
    waiting = port.in_waiting
    if waiting:
        frame.extend(port.read(min(waiting, 256)))
    return bytes(frame)
