"""MOOSApp that posts APPCAST reports for uMAC and pMarineViewer."""

import time as _wallclock

from pymoos2.core.time import moos_time
from pymoos2.core.MOOSApp import MOOSApp

OSEP = "!@#"
ISEP = "!@"


class AppCastingMOOSApp(MOOSApp):
    """MOOS application with AppCasting.

    Override on_startup(), register_variables(), on_new_mail(), iterate() and
    build_report().
    """

    def __init__(self):
        super().__init__()
        self._report_lines = []
        self._events = []
        self._run_warnings = {}
        self._run_warning_total = 0
        self._config_warnings = []
        self._max_events = 20
        self._last_report_time = 0.0
        self._term_report_interval = 0.5
        self._warnings_changed = False

        self._appcast_requests = {}

    def report(self, text):
        """Append a line, a multi-line string or an ACTable to the report."""
        self._report_lines.append(str(text))

    def report_event(self, event):
        """Add a timestamped event to the appcast."""
        ts = moos_time() - self.m_start_time
        self._events.append(f"[{ts:.2f}]: {event}")
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def report_run_warning(self, warning):
        """Add a run warning; repeats are counted."""
        self._run_warnings[warning] = self._run_warnings.get(warning, 0) + 1
        self._run_warning_total += 1
        self._warnings_changed = True

    def retract_run_warning(self, warning):
        """Remove a runtime warning."""
        count = self._run_warnings.pop(warning, 0)
        if count:
            self._run_warning_total = max(0, self._run_warning_total - count)
            self._warnings_changed = True

    def report_config_warning(self, warning):
        """Add a configuration warning."""
        if warning not in self._config_warnings:
            self._config_warnings.append(warning)
            self._warnings_changed = True

    def set_max_events(self, n):
        self._max_events = max(1, int(n))

    def build_report(self):
        """Fill the report with self.report(); return True to post it."""
        return True

    def _pre_startup(self):
        self.register("APPCAST_REQ", 0.0)
        self.register("TERM_REPORT_INTERVAL", 0.0)
        self._term_report_interval = self.config(
            "term_report_interval", default=0.5, type=float)
        if self._term_report_interval < 0.0 or self._term_report_interval > 10.0:
            self._term_report_interval = 0.5

    def _filter_mail(self, mail):
        user_mail = []
        for msg in mail:
            if msg.name == "APPCAST_REQ":
                self._handle_appcast_req(msg.string())
            elif msg.name == "TERM_REPORT_INTERVAL":
                try:
                    self._term_report_interval = max(0.4, float(msg.string() if msg.is_string() else msg.double()))
                except ValueError:
                    pass
            else:
                user_mail.append(msg)
        return user_mail

    def _handle_appcast_req(self, req_str):
        params = {}
        for token in req_str.split(","):
            if "=" in token:
                k, v = token.split("=", 1)
                params[k.strip().lower()] = v.strip()

        req_node = params.get("node", "")
        req_app = params.get("app", "")
        key = params.get("key", "")
        thresh = params.get("thresh", "any").lower()
        try:
            duration = float(params.get("duration", "3"))
        except ValueError:
            duration = 3.0
        duration = min(max(duration, 0.0), 30.0)

        if not key:
            return
        if req_node and req_node != "all" and req_node != self.m_community:
            return
        if req_app and req_app != "all" and req_app != self.m_app_name:
            return
        if thresh not in ("any", "run_warning"):
            thresh = "any"

        self._appcast_requests[key] = (moos_time() + duration, thresh)

    def _appcast_requested(self):
        now = moos_time()
        self._appcast_requests = {
            k: v for k, v in self._appcast_requests.items() if v[0] > now
        }
        if not self._appcast_requests:
            return False
        if any(thresh == "any" for _, thresh in self._appcast_requests.values()):
            return True
        return self._warnings_changed

    def _post_iterate(self):
        if self.m_iteration > 1:
            if not self._appcast_requested():
                return
            if _wallclock.time() - self._last_report_time < self._term_report_interval:
                return

        self._report_lines = []
        should_post = self.build_report()

        if should_post:
            self._post_appcast()
            self._last_report_time = _wallclock.time()
            self._warnings_changed = False

    def get_appcast_string(self):
        """The APPCAST value for this app."""
        parts = [f"proc={self.m_app_name}", f"iter={self.m_iteration}"]
        if self.m_community:
            parts.append(f"node={self.m_community}")
        parts.append(f"iter={self.m_iteration}")

        body = "\n".join(self._report_lines)
        lines = body.split("\n") if body else []
        parts.append("messages=" + "".join(line + ISEP for line in lines))

        if self._config_warnings:
            parts.append("config_warnings=" + ISEP.join(self._config_warnings))
        else:
            parts.append("")

        parts.append(f"events_total={len(self._events)}")
        if self._events:
            parts.append("events=" + ISEP.join(self._events))
        else:
            parts.append("")

        parts.append(f"run_warning_total={self._run_warning_total}")
        if self._run_warnings:
            warnings_strs = [f"{count}:{text}" for text, count in self._run_warnings.items()]
            parts.append("run_warnings=" + ISEP.join(warnings_strs))
        else:
            parts.append("")

        return OSEP.join(parts)

    def _post_appcast(self):
        self.notify("APPCAST", self.get_appcast_string())

    def _report_iterate_error(self, err_msg):
        self.report_run_warning(err_msg)
