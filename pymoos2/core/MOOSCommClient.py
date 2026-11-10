"""Threaded client for the MOOSDB.

notify() and register() queue messages for the comms thread; fetch() drains
received mail.
"""

import numbers
import socket
import struct
import threading
import time
import traceback

from pymoos2.core.time import moos_pause, moos_local_time

from pymoos2.core.constants import (
    PROTOCOL_STRING, PROTOCOL_STRING_BUFFER_SIZE,
    MSG_NULL, MSG_DATA, MSG_WELCOME, MSG_POISON, MSG_NOTIFY, MSG_REGISTER,
    MSG_UNREGISTER, MSG_WILDCARD_REGISTER, MSG_WILDCARD_UNREGISTER,
    DATA_STRING, DATA_BINARY,
    DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT,
)
from pymoos2.core.MOOSMsg import MOOSMsg
from pymoos2.core.MOOSCommPkt import HEADER_SIZE, pack as pkt_pack, unpack as pkt_unpack

CONNECT_TIMEOUT_S = 5.0
REPLY_TIMEOUT_S = 10.0
RETRY_PERIOD_S = 1.0
MAX_PACKET_BYTES = 64 * 1024 * 1024
_LINK_ERRORS = (OSError, ConnectionError, ValueError, struct.error)


def wildcard_spec(var_pattern, app_pattern="*", interval=0.0):
    """Registration string for a wildcard subscription."""
    return f"AppPattern={app_pattern},VarPattern={var_pattern},Interval={float(interval):g}"


class MOOSCommClient:
    def __init__(self, server_host=DEFAULT_SERVER_HOST, server_port=DEFAULT_SERVER_PORT,
                 app_name="pymoos2", comm_tick=4.0):
        if not app_name:
            raise ValueError("app_name is required: MOOSDB identifies clients by name")
        if not comm_tick or comm_tick <= 0:
            raise ValueError(f"comm_tick must be positive, got {comm_tick!r}")
        self.server_host = server_host
        self.server_port = int(server_port)
        self.app_name = app_name
        self.comm_tick = float(comm_tick)
        self.last_error = ""
        self._reported = set()

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
        self._wildcards = {}

        self._mail_callback = None
        self._ever_connected = False
        self._reconnect_pending = False
        self._state_lock = threading.Lock()

    @property
    def community(self):
        return self._community

    @property
    def skew(self):
        return self._skew

    @property
    def is_connected(self):
        return self._connected

    def start(self):
        """Start the comms thread; raises RuntimeError if it is already running."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError(f"{self.app_name}: comms thread already running")
        self._running = True
        self._thread = threading.Thread(target=self._comms_loop, daemon=True,
                                        name=f"{self.app_name}-comms")
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

    def set_mail_callback(self, callback):
        """Call fn() on the comms thread whenever mail arrives; keep it short and
        thread safe.
        """
        self._mail_callback = callback

    def consume_reconnect(self):
        """True once after each reconnection."""
        with self._state_lock:
            flag = self._reconnect_pending
            self._reconnect_pending = False
        return flag

    def notify(self, key, value, time_val=-1.0, src_aux=""):
        """Queue a NOTIFY.

        bool posts "true"/"false", real numbers post doubles, bytes post binary
        and str posts a string. Other types raise TypeError.
        """
        if not isinstance(key, str):
            raise TypeError(f"MOOS variable name must be str, not {type(key).__name__}")
        if not key:
            raise ValueError("notify needs a variable name")
        if isinstance(value, bool) or getattr(getattr(value, "dtype", None), "kind", "") == "b":
            msg = MOOSMsg(MSG_NOTIFY, key, sval="true" if value else "false",
                          time=time_val, data_type=DATA_STRING)
        elif isinstance(value, numbers.Real):
            msg = MOOSMsg(MSG_NOTIFY, key, val=float(value), time=time_val)
        elif isinstance(value, (bytes, bytearray)):
            msg = MOOSMsg(MSG_NOTIFY, key, sval=bytes(value), time=time_val, data_type=DATA_BINARY)
        elif isinstance(value, str):
            msg = MOOSMsg(MSG_NOTIFY, key, sval=value, time=time_val,
                          data_type=DATA_STRING)
        else:
            raise TypeError(f"cannot post {type(value).__name__} to {key}; use str, bytes, bool or a number")
        msg.src = self.app_name
        msg.src_aux = src_aux
        msg.community = self._community
        with self._outbox_lock:
            self._outbox.append(msg)

    def register(self, var_name, interval=0.0):
        """Subscribe to a variable; kept across reconnects."""
        self._subscriptions[var_name] = interval
        self._queue(self._register_msg(var_name, interval))

    def unregister(self, var_name):
        """Queue an UNREGISTER message."""
        self._subscriptions.pop(var_name, None)
        msg = MOOSMsg(MSG_UNREGISTER, var_name, val=0.0)
        msg.src = self.app_name
        self._queue(msg)

    def wildcard_register(self, var_pattern, app_pattern="*", interval=0.0):
        """Subscribe to a wildcard pattern; kept across reconnects."""
        self._wildcards[(var_pattern, app_pattern)] = interval
        self._queue(self._wildcard_msg(MSG_WILDCARD_REGISTER, var_pattern,
                                       app_pattern, interval))

    def wildcard_unregister(self, var_pattern, app_pattern="*"):
        """Queue a WILDCARD_UNREGISTER message."""
        self._wildcards.pop((var_pattern, app_pattern), None)
        self._queue(self._wildcard_msg(MSG_WILDCARD_UNREGISTER, var_pattern,
                                       app_pattern, 0.0))

    def fetch(self):
        """Drain and return all inbox messages."""
        with self._inbox_lock:
            msgs = self._inbox
            self._inbox = []
        return msgs

    def _register_msg(self, var_name, interval):
        msg = MOOSMsg(MSG_REGISTER, var_name, val=interval)
        msg.src = self.app_name
        return msg

    def _wildcard_msg(self, msg_type, var_pattern, app_pattern, interval):
        spec = wildcard_spec(var_pattern, app_pattern, interval)
        msg = MOOSMsg(msg_type, self.app_name, sval=spec, data_type=DATA_STRING)
        msg.src = self.app_name
        return msg

    def _queue(self, msg):
        with self._outbox_lock:
            self._outbox.append(msg)

    def _live_sock(self):
        sock = self._sock
        if sock is None:
            raise ConnectionError("connection closed")
        return sock

    def _send_raw(self, data):
        self._live_sock().sendall(data)

    def _recv_raw(self, nbytes):
        buf = bytearray()
        while len(buf) < nbytes:
            chunk = self._live_sock().recv(nbytes - len(buf))
            if not chunk:
                raise ConnectionError("MOOSDB closed connection")
            buf.extend(chunk)
        return bytes(buf)

    def _send_pkt(self, msgs):
        self._send_raw(pkt_pack(msgs))

    def _recv_pkt(self):
        header = self._recv_raw(4)
        (byte_count,) = struct.unpack("<i", header)
        if not HEADER_SIZE <= byte_count <= MAX_PACKET_BYTES:
            raise ConnectionError(f"implausible packet length {byte_count} from MOOSDB")
        body = self._recv_raw(byte_count - 4)
        return pkt_unpack(header + body)

    def _connect(self):
        try:
            self._handshake()
        except BaseException:
            self._close()
            raise

    def _handshake(self):
        sock = socket.create_connection((self.server_host, self.server_port), timeout=CONNECT_TIMEOUT_S)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(REPLY_TIMEOUT_S)
        self._sock = sock

        proto = PROTOCOL_STRING.ljust(PROTOCOL_STRING_BUFFER_SIZE, b"\x00")
        self._send_raw(proto)

        reg_msg = MOOSMsg(MSG_DATA, "", sval=self.app_name, data_type=DATA_STRING)
        reg_msg.src = self.app_name
        self._send_pkt([reg_msg])

        reply_msgs = self._recv_pkt()
        if not reply_msgs:
            raise ConnectionError("Empty handshake reply from MOOSDB")

        welcome = reply_msgs[0]
        if welcome.msg_type == MSG_POISON:
            reason = welcome.string() if welcome.is_string() else "unknown"
            raise ConnectionError(f"MOOSDB rejected connection: {reason}")

        if welcome.msg_type != MSG_WELCOME:
            raise ConnectionError(f"unexpected handshake reply type {chr(welcome.msg_type)!r}")
        self._community = welcome.community
        self._skew = welcome.val

        with self._state_lock:
            if self._ever_connected:
                self._reconnect_pending = True
            self._ever_connected = True
        self._connected = True
        self._connect_event.set()
        self._replay_subscriptions()

    def _replay_subscriptions(self):
        with self._outbox_lock:
            for var_name, interval in self._subscriptions.items():
                self._outbox.append(self._register_msg(var_name, interval))
            for (var_pattern, app_pattern), interval in self._wildcards.items():
                self._outbox.append(self._wildcard_msg(
                    MSG_WILDCARD_REGISTER, var_pattern, app_pattern, interval))

    def _close(self):
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _requeue(self, msgs):
        msgs = [m for m in msgs if m.msg_type != MSG_NULL]
        if msgs:
            with self._outbox_lock:
                self._outbox[:0] = msgs

    def _link_failed(self, e):
        """Record why the link dropped; unexpected errors print their traceback once per kind."""
        self.last_error = f"{type(e).__name__}: {e}"
        if not isinstance(e, _LINK_ERRORS) and type(e) not in self._reported:
            self._reported.add(type(e))
            print(f"  ** {self.app_name} comms: {self.last_error}; retrying", flush=True)
            traceback.print_exc()

    def _comms_loop(self):
        comm_period_ms = 1000.0 / self.comm_tick
        while self._running:
            if not self._connected:
                try:
                    self._connect()
                except Exception as e:
                    self._link_failed(e)
                    time.sleep(RETRY_PERIOD_S)
                    continue

            to_send = []
            sent = False
            try:
                t0 = moos_local_time()

                with self._outbox_lock:
                    to_send = self._outbox
                    self._outbox = []
                if not to_send:
                    to_send = [MOOSMsg(MSG_NULL, "", src=self.app_name)]

                self._send_pkt(to_send)
                sent = True
                incoming = self._recv_pkt()

                real_msgs = [m for m in incoming if m.msg_type != MSG_NULL]
                if real_msgs:
                    with self._inbox_lock:
                        self._inbox.extend(real_msgs)
                    cb = self._mail_callback
                    if cb is not None:
                        try:
                            cb()
                        except Exception:
                            pass
                elapsed_ms = (moos_local_time() - t0) * 1000.0
                sleep_ms = comm_period_ms - elapsed_ms
                if sleep_ms > 1:
                    moos_pause(sleep_ms)

            except Exception as e:
                self._link_failed(e)
                if not sent:
                    self._requeue(to_send)
                self._close()
                self._connect_event.clear()
                if self._running:
                    time.sleep(RETRY_PERIOD_S)
