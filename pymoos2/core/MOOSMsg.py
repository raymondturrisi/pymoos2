"""MOOS message and its binary encoding.

Text is UTF-8 with surrogateescape, so any bytes round-trip unchanged.
"""

import itertools
import struct

from pymoos2.core.constants import (
    MSG_NOT_SET,
    DATA_DOUBLE, DATA_STRING, DATA_BINARY,
)
from pymoos2.core.time import moos_time

_ID_COUNTER = itertools.count()
_ENC = "utf-8"
_ERR = "surrogateescape"
_MIN_MSG_BYTES = 4 + 4 + 2 + 4 * 4 + 24 + 4


def _text(b):
    return bytes(b).decode(_ENC, _ERR)


def _bytes(s):
    return s if isinstance(s, (bytes, bytearray)) else s.encode(_ENC, _ERR)


class MOOSMsg:
    __slots__ = (
        "msg_type", "data_type", "key", "msg_id",
        "time", "val", "val2",
        "sval", "src", "src_aux", "community",
    )

    def __init__(self, msg_type=MSG_NOT_SET, key="", val=0.0, sval="",
                 src="", time=-1.0, data_type=None):
        """data_type defaults from data: a non-empty str is a string, non-empty
        bytes are binary, anything else is a double. Pass DATA_STRING to send an
        empty string.
        """
        self.msg_type = msg_type
        self.key = key
        self.src = src
        self.src_aux = ""
        self.community = ""
        self.msg_id = next(_ID_COUNTER)
        self.time = time if time >= 0 else moos_time()
        self.val2 = 0.0
        self.val = float(val)

        if data_type is None:
            if isinstance(sval, str) and sval:
                data_type = DATA_STRING
            elif isinstance(sval, (bytes, bytearray)) and sval:
                data_type = DATA_BINARY
            else:
                data_type = DATA_DOUBLE
        self.data_type = data_type

        if data_type == DATA_STRING:
            self.sval = sval if isinstance(sval, str) else _text(sval)
        elif data_type == DATA_BINARY:
            self.sval = bytes(sval) if sval else b""
        else:
            self.sval = ""

    @property
    def name(self):
        return self.key

    def double(self):
        return self.val

    def string(self):
        return self.sval if isinstance(self.sval, str) else _text(self.sval)

    def binary_data(self):
        return self.sval if isinstance(self.sval, bytes) else _bytes(self.sval)

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
        s = _bytes(s)
        return struct.pack("<i", len(s)) + s

    @staticmethod
    def _unpack_string(buf, offset, end):
        (length,) = struct.unpack_from("<i", buf, offset)
        offset += 4
        if length < 0 or offset + length > end:
            raise ValueError(f"string field of {length} bytes runs past the message")
        return bytes(buf[offset:offset + length]), offset + length

    def serialize(self):
        """Encode as bytes."""
        sval_bytes = _bytes(self.sval)
        payload = b"".join((
            struct.pack("<i", self.msg_id),
            struct.pack("<BB", self.msg_type, self.data_type),
            self._pack_string(self.src),
            self._pack_string(self.src_aux),
            self._pack_string(self.community),
            self._pack_string(self.key),
            struct.pack("<3d", self.time, self.val, self.val2),
            self._pack_string(sval_bytes),
        ))
        return struct.pack("<i", len(payload) + 4) + payload

    @classmethod
    def deserialize(cls, buf, offset=0):
        """Decode the message at offset; returns (msg, new_offset). Raises
        ValueError on malformed data.
        """
        start = offset
        try:
            (total_len,) = struct.unpack_from("<i", buf, offset)
            end = start + total_len
            if total_len < _MIN_MSG_BYTES or end > len(buf):
                raise ValueError(f"message length {total_len} does not fit the {len(buf) - start} bytes left")
            offset += 4
            (msg_id,) = struct.unpack_from("<i", buf, offset); offset += 4
            (msg_type, data_type) = struct.unpack_from("<BB", buf, offset); offset += 2

            src, offset = cls._unpack_string(buf, offset, end)
            src_aux, offset = cls._unpack_string(buf, offset, end)
            community, offset = cls._unpack_string(buf, offset, end)
            key, offset = cls._unpack_string(buf, offset, end)

            if offset + 24 > end:
                raise ValueError("message ends inside its numeric fields")
            (time_val, val, val2) = struct.unpack_from("<3d", buf, offset); offset += 24

            sval, offset = cls._unpack_string(buf, offset, end)
        except struct.error as e:
            raise ValueError(f"truncated message: {e}") from None
        if data_type not in (DATA_DOUBLE, DATA_STRING, DATA_BINARY):
            raise ValueError(f"unknown data type {data_type!r}")

        msg = cls.__new__(cls)
        msg.msg_type = msg_type
        msg.data_type = data_type
        msg.key = _text(key)
        msg.msg_id = msg_id
        msg.time = time_val
        msg.val = val
        msg.val2 = val2
        msg.src = _text(src)
        msg.src_aux = _text(src_aux)
        msg.community = _text(community)
        msg.sval = sval if data_type == DATA_BINARY else _text(sval)

        return msg, end

    def __repr__(self):
        dtype = {DATA_DOUBLE: "D", DATA_STRING: "S", DATA_BINARY: "B"}.get(self.data_type, "?")
        return f"MOOSMsg({chr(self.msg_type)}/{dtype} {self.key}={self.val if self.is_double() else repr(self.sval)})"
