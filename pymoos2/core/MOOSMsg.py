"""
MOOS message class with binary serialization.
"""

import struct

from pymoos2.core.constants import (
    MSG_NOTIFY, MSG_NULL, MSG_NOT_SET,
    DATA_DOUBLE, DATA_STRING, DATA_BINARY,
)
from pymoos2.core.time import moos_time


class MOOSMsg:
    __slots__ = (
        "msg_type", "data_type", "key", "msg_id",
        "time", "val", "val2",
        "sval", "src", "src_aux", "community",
    )

    _next_id = 0

    def __init__(self, msg_type=MSG_NOT_SET, key="", val=0.0, sval="",
                 src="", time=-1.0):
        self.msg_type = msg_type
        self.key = key
        self.src = src
        self.src_aux = ""
        self.community = ""
        self.msg_id = MOOSMsg._next_id
        MOOSMsg._next_id += 1
        self.time = time if time >= 0 else moos_time()
        self.val2 = 0.0

        if isinstance(sval, str) and sval:
            self.data_type = DATA_STRING
            self.val = val
            self.sval = sval
        elif isinstance(sval, (bytes, bytearray)) and sval:
            self.data_type = DATA_BINARY
            self.val = val
            self.sval = sval
        else:
            self.data_type = DATA_DOUBLE
            self.val = val
            self.sval = ""

    @property
    def name(self):
        return self.key

    def double(self):
        return self.val

    def string(self):
        return self.sval if isinstance(self.sval, str) else self.sval.decode()

    def binary_data(self):
        return self.sval if isinstance(self.sval, bytes) else self.sval.encode()

    def source(self):
        return self.src

    def is_double(self):
        return self.data_type == DATA_DOUBLE

    def is_string(self):
        return self.data_type == DATA_STRING

    def is_binary(self):
        return self.data_type == DATA_BINARY

    def is_name(self, name):
        return self.key == name

    @staticmethod
    def _pack_string(s):
        """Length-prefixed string: [4-byte len][raw bytes]."""
        if isinstance(s, str):
            s = s.encode()
        return struct.pack("<i", len(s)) + s

    @staticmethod
    def _unpack_string(buf, offset):
        """Returns (string_bytes, new_offset)."""
        (length,) = struct.unpack_from("<i", buf, offset)
        offset += 4
        data = buf[offset:offset + length]
        offset += length
        return data, offset

    def serialize(self):
        """Serialize this message to bytes (matches CMOOSMsg::Serialize TO_STREAM)."""
        payload = struct.pack("<i", self.msg_id)
        payload += struct.pack("<BB", self.msg_type, self.data_type)
        payload += self._pack_string(self.src)
        payload += self._pack_string(self.src_aux)
        payload += self._pack_string(self.community)
        payload += self._pack_string(self.key)
        payload += struct.pack("<3d", self.time, self.val, self.val2)
        sval_bytes = self.sval if isinstance(self.sval, bytes) else self.sval.encode()
        payload += self._pack_string(sval_bytes)
        return struct.pack("<i", len(payload) + 4) + payload

    @classmethod
    def deserialize(cls, buf, offset=0):
        """Deserialize a message from buf at offset. Returns (MOOSMsg, new_offset)."""
        start = offset
        (total_len,) = struct.unpack_from("<i", buf, offset); offset += 4
        (msg_id,) = struct.unpack_from("<i", buf, offset); offset += 4
        (msg_type, data_type) = struct.unpack_from("<BB", buf, offset); offset += 2

        src, offset = cls._unpack_string(buf, offset)
        src_aux, offset = cls._unpack_string(buf, offset)
        community, offset = cls._unpack_string(buf, offset)
        key, offset = cls._unpack_string(buf, offset)

        (time_val, val, val2) = struct.unpack_from("<3d", buf, offset); offset += 24

        sval, offset = cls._unpack_string(buf, offset)

        msg = cls.__new__(cls)
        msg.msg_type = msg_type
        msg.data_type = data_type
        msg.key = key.decode()
        msg.msg_id = msg_id
        msg.time = time_val
        msg.val = val
        msg.val2 = val2
        msg.src = src.decode()
        msg.src_aux = src_aux.decode()
        msg.community = community.decode()
        msg.sval = sval if data_type == DATA_BINARY else sval.decode()

        return msg, start + total_len

    def __repr__(self):
        dtype = {DATA_DOUBLE: "D", DATA_STRING: "S", DATA_BINARY: "B"}.get(self.data_type, "?")
        return f"MOOSMsg({chr(self.msg_type)}/{dtype} {self.key}={self.val if self.is_double() else repr(self.sval)})"
