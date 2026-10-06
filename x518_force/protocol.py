"""X518 read-only Modbus RTU protocol; no serial or third-party dependencies."""

import struct

MEASUREMENT_ADDRESS = 0x0A00
MEASUREMENT_REGISTERS = 4


class ProtocolError(ValueError):
    """Invalid, incomplete, or corrupt response (never a measurement)."""


class ModbusException(ProtocolError):
    def __init__(self, code):
        self.code = code
        meanings = {
            1: "illegal function", 2: "illegal address", 3: "illegal value",
            4: "device failure", 5: "acknowledge", 6: "device busy",
            10: "gateway path unavailable", 11: "gateway target timeout",
        }
        super().__init__(f"Modbus exception 0x{code:02X}: {meanings.get(code, 'unknown')}")


def crc16(data):
    """Return Modbus CRC16; wire order is low byte followed by high byte."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def append_crc(data):
    return data + struct.pack("<H", crc16(data))


def build_read_request(slave=1):
    # Intentionally fixed address and function: no arbitrary writes or scans.
    if not 1 <= slave <= 247:
        raise ValueError("slave must be 1..247 (broadcast reads are forbidden)")
    return append_crc(struct.pack(">BBHH", slave, 3, MEASUREMENT_ADDRESS,
                                  MEASUREMENT_REGISTERS))


def decode_int32(data, word_swap=False):
    if len(data) != 4:
        raise ProtocolError(f"int32 requires 4 bytes, received {len(data)}")
    if word_swap:
        data = data[2:4] + data[0:2]
    return struct.unpack(">i", data)[0]


def parse_measurement_response(frame, slave=1, word_swap=False):
    if not frame:
        raise ProtocolError("timeout: empty response")
    if len(frame) < 5:
        raise ProtocolError(f"short frame: received {len(frame)} bytes, minimum 5")
    if frame[0] != slave:
        raise ProtocolError(f"wrong slave: expected {slave}, received {frame[0]}")
    function = frame[1]
    if function not in (3, 0x83):
        raise ProtocolError(f"wrong function: expected 03/83, received {function:02X}")
    expected_length = 5 if function == 0x83 else 13
    if len(frame) != expected_length:
        raise ProtocolError(f"frame length: expected {expected_length}, received {len(frame)}")
    actual_crc = int.from_bytes(frame[-2:], "little")
    expected_crc = crc16(frame[:-2])
    if actual_crc != expected_crc:
        raise ProtocolError(f"CRC mismatch: expected {expected_crc:04X}, received {actual_crc:04X}")
    if function == 0x83:
        raise ModbusException(frame[2])
    if frame[2] != 8:
        raise ProtocolError(f"byte count: expected 8, received {frame[2]}")
    return (decode_int32(frame[3:7], word_swap),
            decode_int32(frame[7:11], word_swap))


if __name__ == "__main__":
    print("This file is the protocol module. Start acquisition with:")
    print("  python x518_reader.py")
    print("Or read COM3 directly with:")
    print("  python x518_reader.py --port COM3 --debug")
