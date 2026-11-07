"""Base MOOS application: configuration, comms and the app loop."""

import fnmatch
import os
import socket
import struct
import threading
import time as _wallclock
import traceback

from pymoos2.core.constants import (
    DEFAULT_APP_TICK, DEFAULT_COMMS_TICK,
    DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT,
    SUICIDE_MULTICAST_ADDR, SUICIDE_MULTICAST_PORT, SUICIDE_DEFAULT_PHRASE,
)
from pymoos2.core.time import (
    set_moos_time_warp, get_moos_time_warp, set_moos_skew,
    moos_local_time, moos_time, moos_pause,
)
from pymoos2.core.MOOSCommClient import MOOSCommClient
from pymoos2.core.MissionReader import MissionReader


class MOOSApp:
    """Subclass and override on_startup(), register_variables(), on_new_mail()
    and iterate().
    """

    def __init__(self):
        self.m_app_name = ""
        self.m_mission_file = ""
        self.m_mission_reader = None
        self.m_comms = None

        self.m_iteration = 0
        self.m_start_time = 0.0
        self.m_last_iterate_time = 0.0
        self.m_time_warp = 1.0
        self.m_community = ""

        self.m_app_tick = DEFAULT_APP_TICK
        self.m_comm_tick = DEFAULT_COMMS_TICK

        self._running = False
        self._shut_down = False
        self._suicide_thread = None

        self._debug = False
        self._debug_stream = None
        self._debug_fname = ""

    def config(self, key, default=None, type=str):
        """Read a parameter from this app's ProcessConfig block (last value wins)."""
        if self.m_mission_reader:
            return self.m_mission_reader.get_config(key, default=default, type=type)
        return default

    def config_lines(self):
        """All (key, value) lines of this app's ProcessConfig block, in file order."""
        if self.m_mission_reader:
            return self.m_mission_reader.get_config_lines()
        return []

    def global_config(self, key, default=None, type=str):
        """Read a global (top-level) mission file parameter."""
        if self.m_mission_reader:
            return self.m_mission_reader.get_value(key, default=default, type=type)
        return default

    def register(self, var_name, interval=0.0):
        """Register for a MOOS variable."""
        if self.m_comms:
            self.m_comms.register(var_name, interval)

    def unregister(self, var_name):
        """Unregister from a MOOS variable."""
        if self.m_comms:
            self.m_comms.unregister(var_name)

    def wildcard_register(self, var_pattern, app_pattern="*", interval=0.0):
        """Register for MOOS variables matching a wildcard pattern."""
        if self.m_comms:
            self.m_comms.wildcard_register(var_pattern, app_pattern, interval)

    def wildcard_unregister(self, var_pattern, app_pattern="*"):
        """Drop a wildcard registration."""
        if self.m_comms:
            self.m_comms.wildcard_unregister(var_pattern, app_pattern)

    def notify(self, key, value, time_val=-1.0, src_aux=""):
        """Publish a MOOS variable."""
        if self.m_comms:
            self.m_comms.notify(key, value, time_val=time_val, src_aux=src_aux)

    def dbg_print(self, fmt, *args):
        """Write a line to the debug file when debug=true is configured."""
        if not self._debug:
            return
        if self._debug_stream is None:
            ts = _wallclock.strftime("%Y-%m-%d_%H:%M:%S")
            self._debug_fname = f"DBG_{self.m_app_name}_{ts}_DATA.dbg"
            try:
                self._debug_stream = open(self._debug_fname, "a")
            except OSError:
                self._debug = False
                return
        line = fmt % args if args else fmt
        self._debug_stream.write(line + "\n")
        self._debug_stream.flush()

    def on_startup(self):
        """Called once after connecting. Read configuration here."""
        pass

    def on_connect_to_server(self):
        """Called on every connect and reconnect; calls register_variables()."""
        self.register_variables()

    def register_variables(self):
        """Register subscriptions. Override this."""
        pass

    def on_new_mail(self, mail):
        """Called with new mail each iteration. Override this."""
        pass

    def iterate(self):
        """Called at AppTick. Override this."""
        pass

    def _pre_startup(self):
        """Hook run before on_startup()."""
        pass

    def _filter_mail(self, mail):
        """Hook: return the mail to pass to on_new_mail()."""
        return mail

    def _post_iterate(self):
        """Hook run after iterate()."""
        pass

    def _report_iterate_error(self, err_msg):
        pass

    def _initialize(self, app_name, mission_file):
        self.m_app_name = app_name
        self.m_mission_file = mission_file

    def _shutdown(self):
        """Shut down; safe to call more than once."""
        self._running = False
        if self._shut_down:
            return
        self._shut_down = True
        if self.m_comms and self.m_comms.is_connected:
            self.m_comms.notify("EXITED_NORMALLY", self.m_app_name)
            _wallclock.sleep(0.2)
        if self.m_comms:
            self.m_comms.stop()
        if self._debug_stream:
            self._debug_stream.close()

    def _run(self):
        self._running = True

        self.m_mission_reader = MissionReader(self.m_mission_file, self.m_app_name)

        self.m_app_tick = self.m_mission_reader.get_config(
            "apptick", default=DEFAULT_APP_TICK, type=float)
        self.m_comm_tick = self.m_mission_reader.get_config(
            "commstick", default=DEFAULT_COMMS_TICK, type=float)
        self.m_time_warp = self.m_mission_reader.get_value(
            "MOOSTimeWarp", default=1.0, type=float)
        try:
            set_moos_time_warp(self.m_time_warp)
        except ValueError as e:
            print(f"  ** {self.m_app_name}: {e}; running at time warp 1")
            self.m_time_warp = 1.0
            set_moos_time_warp(1.0)
        self._debug = self.m_mission_reader.get_config(
            "debug", default=False, type=bool)
        if self.m_app_tick <= 0:
            self.m_app_tick = DEFAULT_APP_TICK
        if self.m_comm_tick <= 0:
            self.m_comm_tick = DEFAULT_COMMS_TICK

        server_host = self.m_mission_reader.get_value(
            "ServerHost", default=DEFAULT_SERVER_HOST)
        server_port = self.m_mission_reader.get_value(
            "ServerPort", default=DEFAULT_SERVER_PORT, type=int)

        self._print_banner(server_host, server_port)

        self.m_comms = MOOSCommClient(
            server_host, server_port, self.m_app_name, self.m_comm_tick)
        self.m_comms.start()

        if not self.m_comms.wait_until_connected(timeout=10.0):
            print(f"  ** WARNING: {self.m_app_name} failed to connect to MOOSDB "
                  f"at {server_host}:{server_port}")

        set_moos_skew(self.m_comms.skew)

        self.m_community = self.m_mission_reader.get_value("Community", default="")
        if not self.m_community:
            self.m_community = self.m_comms.community

        self._start_suicide_listener()

        self.m_start_time = moos_local_time()
        self._pre_startup()
        self.on_startup()
        self.on_connect_to_server()
        self.m_comms.consume_reconnect()

        app_period_ms = 1000.0 / self.m_app_tick
        self.m_last_iterate_time = moos_local_time()

        while self._running:
            iter_start = moos_local_time()
            self.m_iteration += 1

            try:
                if self.m_comms.consume_reconnect():
                    set_moos_skew(self.m_comms.skew)
                    self.on_connect_to_server()
                mail = self._filter_mail(self.m_comms.fetch())
                if mail:
                    self.on_new_mail(mail)
                self.iterate()
                self._post_iterate()
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
                print(f"  ** {self.m_app_name} error (iter {self.m_iteration}): {err_msg}")
                traceback.print_exc()
                self._report_iterate_error(err_msg)

            self.m_last_iterate_time = iter_start

            elapsed_ms = (moos_local_time() - iter_start) * 1000.0
            if elapsed_ms < 0:
                elapsed_ms = 0
            sleep_ms = app_period_ms - elapsed_ms
            if sleep_ms > 1:
                moos_pause(sleep_ms)

    def _print_banner(self, host, port):
        print(f"  {self.m_app_name} (pymoos2)")
        print(f"  |-ServerHost: {host}")
        print(f"  |-ServerPort: {port}")
        print(f"  |-AppTick:    {self.m_app_tick} Hz")
        print(f"  |-CommsTick:  {self.m_comm_tick} Hz")
        if self.m_time_warp != 1.0:
            print(f"  |-TimeWarp:   {self.m_time_warp}")
        print()

    def _start_suicide_listener(self):
        phrase = self.m_mission_reader.get_config(
            "moos_suicide_phrase", default=SUICIDE_DEFAULT_PHRASE) \
            if self.m_mission_reader else SUICIDE_DEFAULT_PHRASE

        self._suicide_thread = threading.Thread(
            target=self._suicide_loop, args=(phrase,), daemon=True,
            name=f"{self.m_app_name}-ktm")
        self._suicide_thread.start()

    def _suicide_loop(self, phrase):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind(("", SUICIDE_MULTICAST_PORT))

            mreq = struct.pack(
                "4sl", socket.inet_aton(SUICIDE_MULTICAST_ADDR), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.settimeout(2.0)
        except OSError:
            return

        while self._running:
            try:
                data, _ = sock.recvfrom(1024)
                msg = data.decode(errors="replace")
                parts = msg.split(":")
                if len(parts) >= 3 and parts[0] == "K":
                    rx_phrase = parts[1]
                    pattern = parts[2].strip()
                    if rx_phrase == phrase:
                        if pattern == "*" or fnmatch.fnmatch(self.m_app_name, pattern):
                            print(f"  {self.m_app_name}: received ktm signal, shutting down.")
                            self._shutdown()
                            os._exit(0)
            except socket.timeout:
                continue
            except OSError:
                break
