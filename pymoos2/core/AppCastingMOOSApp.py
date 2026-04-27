"""
AppCastingMOOSApp — MOOSApp with AppCasting support.

Registers for APPCAST_REQ, posts APPCAST reports via build_report(),
and tracks events/warnings.
"""

from pymoos2.core.time import moos_time
from pymoos2.core.MOOSApp import MOOSApp

OSEP = "!@#"
ISEP = "!@"


class AppCastingMOOSApp(MOOSApp):
    """
    MOOS application with AppCasting support.
    Override: on_startup(), on_new_mail(), iterate(), build_report().
    """

    def __init__(self):
        super().__init__()
        self._report_lines = []
        self._events = []
        self._run_warnings = {}
        self._config_warnings = []
        self._max_events = 20
        self._last_report_time = 0.0

        self._appcast_requests = {}

    def report(self, text):
        """Append a line (or multi-line string, or ACTable) to the current report."""
        self._report_lines.append(str(text))

    def report_event(self, event):
        """Add a timestamped event to the appcast."""
        ts = moos_time() - self.m_start_time
        self._events.append(f"[{ts:8.1f}] {event}")
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def report_run_warning(self, warning):
        """Add a runtime warning (tracked with count)."""
        self._run_warnings[warning] = self._run_warnings.get(warning, 0) + 1

    def retract_run_warning(self, warning):
        """Remove a runtime warning."""
        self._run_warnings.pop(warning, None)

    def report_config_warning(self, warning):
        """Add a configuration warning."""
        if warning not in self._config_warnings:
            self._config_warnings.append(warning)

    def build_report(self):
        """
        Build the AppCast report. Override this.
        Use self.report("text") and self.report(actable) to add content.
        Return True to post the report.
        """
        return True

    def on_startup(self):
        """Override in subclass. Base registers for APPCAST_REQ."""
        pass

    def _run(self):
        """Extend parent _run to register for APPCAST_REQ after startup."""
        super_on_startup = self.on_startup
        super_on_new_mail = self.on_new_mail

        def wrapped_on_startup():
            self.register("APPCAST_REQ", 0.0)
            super_on_startup()

        def wrapped_on_new_mail(mail):
            user_mail = []
            for msg in mail:
                if msg.name == "APPCAST_REQ":
                    self._handle_appcast_req(msg.string())
                else:
                    user_mail.append(msg)
            if user_mail:
                super_on_new_mail(user_mail)

        self.on_startup = wrapped_on_startup
        self.on_new_mail = wrapped_on_new_mail
        super()._run()

    def _handle_appcast_req(self, req_str):
        """Parse APPCAST_REQ and track if it targets this app."""
        params = {}
        for token in req_str.split(","):
            if "=" in token:
                k, v = token.split("=", 1)
                params[k.strip().lower()] = v.strip()

        req_node = params.get("node", "")
        req_app = params.get("app", "")
        duration = min(float(params.get("duration", "3")), 30.0)
        key = params.get("key", "unknown")

        if req_node and req_node != "all" and req_node != self.m_community:
            return
        if req_app and req_app != "all" and req_app != self.m_app_name:
            return

        self._appcast_requests[key] = moos_time() + duration

    def _appcast_requested(self):
        """Returns True if any non-expired appcast request exists."""
        now = moos_time()
        self._appcast_requests = {
            k: v for k, v in self._appcast_requests.items() if v > now
        }
        return len(self._appcast_requests) > 0

    def _post_iterate(self):
        """Build and post the AppCast report after each iteration."""
        if not self._appcast_requested():
            return

        self._report_lines = []
        should_post = self.build_report()

        if should_post:
            self._post_appcast()
            self._last_report_time = moos_time()

    def _post_appcast(self):
        """
        Format and Notify the APPCAST string in the wire format
        expected by uMAC / pMarineViewer.
        """
        parts = []

        parts.append(f"proc={self.m_app_name}")
        parts.append(f"iter={self.m_iteration}")
        parts.append(f"node={self.m_community}")

        if self._report_lines:
            msg_body = ISEP.join(self._report_lines)
            parts.append(f"messages={msg_body}")

        if self._config_warnings:
            parts.append("config_warnings=" + ISEP.join(self._config_warnings))

        if self._events:
            parts.append(f"events_total={len(self._events)}")
            parts.append("events=" + ISEP.join(self._events))

        if self._run_warnings:
            total = sum(self._run_warnings.values())
            parts.append(f"run_warning_total={total}")
            warnings_strs = [f"{count}:{text}" for text, count in self._run_warnings.items()]
            parts.append("run_warnings=" + ISEP.join(warnings_strs))

        appcast_str = OSEP.join(parts)
        self.notify("APPCAST", appcast_str)

    def _report_iterate_error(self, err_msg):
        """Surface iterate/on_new_mail exceptions as run warnings in AppCast."""
        self.report_run_warning(err_msg)
