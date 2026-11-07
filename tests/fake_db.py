"""Minimal fake MOOSDB for one client."""

import socket
import struct
import threading

from pymoos2.core.constants import (
    PROTOCOL_STRING_BUFFER_SIZE, MSG_WELCOME, MSG_NULL, MSG_NOTIFY, MSG_POISON,
    DATA_STRING,
)
from pymoos2.core.MOOSMsg import MOOSMsg
from pymoos2.core.MOOSCommPkt import pack, unpack


class FakeDB:
    def __init__(self, community="fake", skew=0.0):
        self.community = community
        self.skew = skew
        self.received = []
        self.outgoing = []
        self.connections = 0
        self._lock = threading.Lock()
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(1)
        self._srv.settimeout(0.2)
        self.port = self._srv.getsockname()[1]
        self._running = True
        self._conn = None
        self._drop_requested = False
        self.reject_next = None
        self.garbage_next = False
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def post(self, key, value, src="fake"):
        msg = MOOSMsg(MSG_NOTIFY, key, sval=value, data_type=DATA_STRING) \
            if isinstance(value, str) else MOOSMsg(MSG_NOTIFY, key, val=float(value))
        msg.src = src
        msg.community = self.community
        with self._lock:
            self.outgoing.append(msg)

    def drop_connection(self):
        self._drop_requested = True

    def stop(self):
        self._running = False
        try:
            self._srv.close()
        except OSError:
            pass
        self._thread.join(timeout=3.0)

    def keys_received(self, msg_type=None):
        with self._lock:
            return [m.key for m in self.received if msg_type is None or m.msg_type == msg_type]

    def msgs_received(self, msg_type=None):
        with self._lock:
            return [m for m in self.received if msg_type is None or m.msg_type == msg_type]

    def _recv_exact(self, conn, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError
            buf.extend(chunk)
        return bytes(buf)

    def _recv_pkt(self, conn):
        header = self._recv_exact(conn, 4)
        (byte_count,) = struct.unpack("<i", header)
        body = self._recv_exact(conn, byte_count - 4)
        return unpack(header + body)

    def _serve(self):
        while self._running:
            try:
                conn, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.connections += 1
            self._drop_requested = False
            try:
                conn.settimeout(5.0)
                self._recv_exact(conn, PROTOCOL_STRING_BUFFER_SIZE)
                self._recv_pkt(conn)
                if self.reject_next is not None:
                    reason, self.reject_next = self.reject_next, None
                    conn.sendall(pack([MOOSMsg(MSG_POISON, "", sval=reason, data_type=DATA_STRING)]))
                    continue
                welcome = MOOSMsg(MSG_WELCOME, "", val=self.skew)
                welcome.community = self.community
                conn.sendall(pack([welcome]))
                while self._running and not self._drop_requested:
                    msgs = self._recv_pkt(conn)
                    with self._lock:
                        self.received.extend(m for m in msgs if m.msg_type != MSG_NULL)
                        reply = self.outgoing
                        self.outgoing = []
                    if self.garbage_next:
                        self.garbage_next = False
                        conn.sendall(struct.pack("<iiB", 20, 1, 0) + b"\xff" * 11)
                        continue
                    if not reply:
                        reply = [MOOSMsg(MSG_NULL, "")]
                    conn.sendall(pack(reply))
            except (OSError, ConnectionError):
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
