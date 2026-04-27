"""
MOOS packet — bundle/unbundle multiple MOOSMsg into a single TCP packet.
"""

import struct
from pymoos2.core.MOOSMsg import MOOSMsg

HEADER_SIZE = 4 + 4 + 1


def pack(msgs):
    """Pack a list of MOOSMsg into a single packet (bytes)."""
    body = b""
    for msg in msgs:
        body += msg.serialize()

    header = struct.pack("<i", HEADER_SIZE + len(body))
    header += struct.pack("<i", len(msgs))
    header += struct.pack("<B", 0)

    return header + body


def unpack(buf):
    """Unpack a packet buffer into a list of MOOSMsg."""
    (byte_count,) = struct.unpack_from("<i", buf, 0)
    (msg_count,) = struct.unpack_from("<i", buf, 4)

    msgs = []
    offset = HEADER_SIZE
    for _ in range(msg_count):
        msg, offset = MOOSMsg.deserialize(buf, offset)
        msgs.append(msg)

    return msgs
