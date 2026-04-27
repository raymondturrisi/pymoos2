"""
MOOS communications client — TCP connection to MOOSDB.
"""

import socket
import struct
import threading
import time

from pymoos2.core.time import moos_pause, moos_local_time

from pymoos2.core.constants import (
    PROTOCOL_STRING, PROTOCOL_STRING_BUFFER_SIZE,
    MSG_NULL, MSG_DATA, MSG_WELCOME, MSG_POISON, MSG_NOTIFY, MSG_REGISTER,
    MSG_UNREGISTER, MSG_WILDCARD_REGISTER,
    DATA_DOUBLE, DATA_STRING,
    DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT,
)
from pymoos2.core.MOOSMsg import MOOSMsg
from pymoos2.core.MOOSCommPkt import pack as pkt_pack, unpack as pkt_unpack, HEADER_SIZE


class MOOSCommClient:
    """Threaded MOOS communications client."""

    def __init__(self, server_host=DEFAULT_SERVER_HOST, server_port=DEFAULT_SERVER_PORT,
                 app_name="pymoos2", comm_tick=4.0):
        self.server_host = server_host
        self.server_port = int(server_port)
        self.app_name = app_name
        self.comm_tick = comm_tick

        self._sock = None
        self._connected = False
        self._running = False
        self._community = ""
        self._skew = 0.0

        self._inbox = []
        self._outbox = []
        self._inbox_lock = threading.Lock()
        self._outbox_lock = threading.Lock()
        self._connect_event = threading.Event()
        self._thread = None

        self._subscriptions = {}

    @property
    def community(self):
        return self._community

    @property
    def is_connected(self):
        return self._connected

    def start(self):
        """Start the comms thread."""
        self._running = True
        self._thread = threading.Thread(target=self._comms_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the comms thread and close socket."""
        self._running = False
        self._close()
        if self._thread:
            self._thread.join(timeout=6.0)

    def wait_until_connected(self, timeout=10.0):
        """Block until connected to MOOSDB or timeout."""
        return self._connect_event.wait(timeout=timeout)

    def notify(self, key, value, time_val=-1.0, src_aux=""):
        """Queue a NOTIFY message."""
        if isinstance(value, (int, float)):
            msg = MOOSMsg(MSG_NOTIFY, key, val=float(value), time=time_val)
        elif isinstance(value, (bytes, bytearray)):
            msg = MOOSMsg(MSG_NOTIFY, key, sval=value, time=time_val)
        else:
            msg = MOOSMsg(MSG_NOTIFY, key, sval=str(value), time=time_val)
        msg.src = self.app_name
        msg.src_aux = src_aux
        msg.community = self._community
        with self._outbox_lock:
            self._outbox.append(msg)

    def register(self, var_name, interval=0.0):
        """Queue a REGISTER message and track for re-registration."""
        self._subscriptions[var_name] = interval
        msg = MOOSMsg(MSG_REGISTER, var_name, val=interval)
        msg.src = self.app_name
        with self._outbox_lock:
            self._outbox.append(msg)

    def unregister(self, var_name):
        """Queue an UNREGISTER message."""
        self._subscriptions.pop(var_name, None)
        msg = MOOSMsg(MSG_UNREGISTER, var_name, val=0.0)
        msg.src = self.app_name
        with self._outbox_lock:
            self._outbox.append(msg)

    def wildcard_register(self, var_pattern, app_pattern="*", interval=0.0):
        """Queue a WILDCARD_REGISTER message."""
        spec = f"AppPattern={app_pattern} VarPattern={var_pattern} Interval={interval}"
        msg = MOOSMsg(MSG_WILDCARD_REGISTER, self.app_name, sval=spec)
        msg.src = self.app_name
        with self._outbox_lock:
            self._outbox.append(msg)

    def fetch(self):
        """Drain and return all inbox messages."""
        with self._inbox_lock:
            msgs = self._inbox
            self._inbox = []
        return msgs

    def _send_raw(self, data):
        """Send all bytes over TCP."""
        self._sock.sendall(data)

    def _recv_raw(self, nbytes):
        """Receive exactly nbytes from TCP."""
        buf = bytearray()
        while len(buf) < nbytes:
            chunk = self._sock.recv(nbytes - len(buf))
            if not chunk:
                raise ConnectionError("MOOSDB closed connection")
            buf.extend(chunk)
        return bytes(buf)

    def _send_pkt(self, msgs):
        """Serialize and send a packet of messages."""
        self._send_raw(pkt_pack(msgs))

    def _recv_pkt(self):
        """Receive and deserialize a packet of messages."""
        header = self._recv_raw(4)
        (byte_count,) = struct.unpack("<i", header)
        remaining = byte_count - 4
        body = self._recv_raw(remaining)
        return pkt_unpack(header + body)

    def _connect(self):
        """TCP connect and handshake with MOOSDB."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(5.0)
        self._sock.connect((self.server_host, self.server_port))
        self._sock.settimeout(None)

        proto = PROTOCOL_STRING.ljust(PROTOCOL_STRING_BUFFER_SIZE, b"\x00")
        self._send_raw(proto)

        reg_msg = MOOSMsg(MSG_DATA, "", sval=self.app_name)
        reg_msg.src = self.app_name
        self._send_pkt([reg_msg])

        reply_msgs = self._recv_pkt()
        if not reply_msgs:
            raise ConnectionError("Empty handshake reply from MOOSDB")

        welcome = reply_msgs[0]
        if welcome.msg_type == MSG_POISON:
            reason = welcome.string() if welcome.is_string() else "unknown"
            raise ConnectionError(f"MOOSDB rejected connection: {reason}")

        if welcome.msg_type == MSG_WELCOME:
            self._community = welcome.community
            self._skew = welcome.val

        self._connected = True
        self._connect_event.set()
        self._replay_subscriptions()

    def _replay_subscriptions(self):
        """Re-register all tracked subscriptions after reconnect."""
        with self._outbox_lock:
            for var_name, interval in self._subscriptions.items():
                msg = MOOSMsg(MSG_REGISTER, var_name, val=interval)
                msg.src = self.app_name
                self._outbox.append(msg)

    def _close(self):
        """Close the TCP socket."""
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _comms_loop(self):
        """Main comms thread: connect, then send/recv at CommsTick."""
        while self._running:
            if not self._connected:
                try:
                    self._connect()
                except (OSError, ConnectionError):
                    time.sleep(1.0)
                    continue

            comm_period_ms = 1000.0 / self.comm_tick
            try:
                t0 = moos_local_time()

                with self._outbox_lock:
                    to_send = self._outbox
                    self._outbox = []
                if not to_send:
                    to_send = [MOOSMsg(MSG_NULL, "", src=self.app_name)]

                self._send_pkt(to_send)
                incoming = self._recv_pkt()

                real_msgs = [m for m in incoming if m.msg_type != MSG_NULL]
                if real_msgs:
                    with self._inbox_lock:
                        self._inbox.extend(real_msgs)
                elapsed_ms = (moos_local_time() - t0) * 1000.0
                sleep_ms = comm_period_ms - elapsed_ms
                if sleep_ms > 1:
                    moos_pause(sleep_ms)

            except (OSError, ConnectionError):
                self._close()
                self._connect_event.clear()
                time.sleep(1.0)
