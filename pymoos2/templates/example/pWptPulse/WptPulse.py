"""
   WptPulse — pymoos2 example vehicle app
   Publishes a VIEW_RANGE_PULSE at the vehicle position each time
   the waypoint index changes.
"""

from pymoos2 import AppCastingMOOSApp, ACTable, moos_time
from pymoos2.dtos.contacts.NodeRecord import NodeRecord
from pymoos2.dtos.geometry.XYRangePulse import XYRangePulse


class WptPulse(AppCastingMOOSApp):
    SYNOPSIS = (
        "Publishes a VIEW_RANGE_PULSE at the vehicle position each time "
        "the helm waypoint index changes. Demonstrates pymoos2 vehicle-side "
        "app with geometry DTOs and NodeRecord parsing."
    )

    VERSION = "0.1.0"

    SUBSCRIPTIONS = [
        "NODE_REPORT_LOCAL  — local vehicle state (string, NodeRecord spec)",
        "WPT_INDEX          — current waypoint index from BHV_Waypoint (double/string)",
    ]

    PUBLICATIONS = [
        "VIEW_RANGE_PULSE   — visual pulse marker at waypoint arrival (string, XYRangePulse spec)",
    ]

    EXAMPLE_CONFIG = """\
ProcessConfig = pWptPulse
{
    AppTick   = 4
    CommsTick = 4

    pulse_radius   = 30.0
    pulse_color    = yellow
    pulse_duration = 4.0
}"""

    def __init__(self):
        super().__init__()
        self.vx = 0.0
        self.vy = 0.0
        self.vname = ""
        self.wpt_index = -1
        self.prev_wpt_index = -1
        self.pulse_count = 0
        self.pulse_radius = 30.0
        self.pulse_color = "yellow"
        self.pulse_duration = 4.0

    def on_startup(self):
        self.pulse_radius = self.config("pulse_radius", default=30.0, type=float)
        self.pulse_color = self.config("pulse_color", default="yellow")
        self.pulse_duration = self.config("pulse_duration", default=4.0, type=float)

    def register_variables(self):
        self.register("NODE_REPORT_LOCAL")
        self.register("WPT_INDEX")

    def on_new_mail(self, mail):
        for msg in mail:
            if msg.name == "NODE_REPORT_LOCAL":
                nr = NodeRecord.from_spec(msg.string())
                self.vx = nr.x
                self.vy = nr.y
                if not self.vname:
                    self.vname = nr.name
            elif msg.name == "WPT_INDEX":
                if msg.is_double():
                    self.wpt_index = int(msg.double())
                else:
                    try:
                        self.wpt_index = int(msg.string())
                    except ValueError:
                        pass

    def iterate(self):
        if self.wpt_index != self.prev_wpt_index and self.prev_wpt_index >= 0:
            pulse = XYRangePulse(
                x=self.vx, y=self.vy,
                radius=self.pulse_radius,
                label=f"wpt_pulse_{self.pulse_count}",
                fill_color=self.pulse_color,
                duration=self.pulse_duration,
                fill=0.6,
            )
            self.notify("VIEW_RANGE_PULSE", pulse.get_spec())
            self.pulse_count += 1
            self.report_event(f"Pulse at wpt {self.wpt_index} ({self.vx:.0f},{self.vy:.0f})")

        self.prev_wpt_index = self.wpt_index

    def build_report(self):
        self.report(f"Vehicle: {self.vname}")
        self.report(f"Position: ({self.vx:.1f}, {self.vy:.1f})")
        self.report("")

        tab = ACTable(["Parameter", "Value"])
        tab.add("Wpt Index", str(self.wpt_index))
        tab.add("Pulse Count", str(self.pulse_count))
        tab.add("Pulse Radius", f"{self.pulse_radius:.0f}")
        tab.add("Pulse Color", self.pulse_color)
        self.report(tab)
        return True
