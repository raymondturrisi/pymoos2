"""Pack and unpack MOOS packets."""

import struct
from pymoos2.core.MOOSMsg import MOOSMsg

HEADER_SIZE = 4 + 4 + 1


def pack(msgs):
    """Pack a list of MOOSMsg into a single packet (bytes)."""
    body = b"".join(msg.serialize() for msg in msgs)
    header = struct.pack("<iiB", HEADER_SIZE + len(body), len(msgs), 0)
    return header + body


def unpack(buf):
    """Unpack a packet into MOOSMsgs; raises ValueError on a malformed or
    compressed packet.
    """
    if len(buf) < HEADER_SIZE:
        raise ValueError(f"packet of {len(buf)} bytes is shorter than its header")
    byte_count, msg_count, compressed = struct.unpack_from("<iiB", buf, 0)
    if byte_count != len(buf):
        raise ValueError(f"packet header says {byte_count} bytes, got {len(buf)}")
    if compressed:
        raise ValueError("compressed packets are not supported")
    if msg_count < 0:
        raise ValueError(f"negative message count {msg_count}")
    msgs = []
    offset = HEADER_SIZE
    for _ in range(msg_count):
        msg, offset = MOOSMsg.deserialize(buf, offset)
        msgs.append(msg)
    if offset != len(buf):
        raise ValueError(f"{len(buf) - offset} stray bytes after {msg_count} messages")
    return msgs
