"""FrameMonitor: publishes local frame distortion at the vehicle and warns past thresholds."""

from pymoos2 import AppCastingMOOSApp, ACTable
from pymoos2.geodesy import distortion

from pframemonitor import __version__
from pframemonitor.frames import frame_from_mission
from pframemonitor.metrics import load_thresholds

METRICS = ("scale_ppm", "convergence_deg", "range_error_m", "bearing_error_deg")


class FrameMonitor(AppCastingMOOSApp):
    SYNOPSIS = "Publishes how far the mission's x/y frame departs from the ground at the vehicle."
    VERSION = __version__
    SUBSCRIPTIONS = ["NAV_X, NAV_Y  vehicle position in the mission frame (double, m)"]
    PUBLICATIONS = ["FRAME_DISTORTION  x=,y=,scale_ppm=,convergence_deg=,range_m=,range_error_m=,bearing_error_deg="]
    EXAMPLE_CONFIG = """\
ProcessConfig = pFrameMonitor
{
  AppTick   = 1
  CommsTick = 4

  projection      = utm                // utm (matches MOOS-IvP apps) or aeqd
  publish_var     = FRAME_DISTORTION
  // thresholds_file = my_limits.json  // default: the package's data/thresholds.json
  // scale_ppm       = 200             // override one limit
}"""

    def __init__(self):
        super().__init__()
        self.frame = None
        self.limits = None
        self.publish_var = "FRAME_DISTORTION"
        self.x = self.y = None
        self.last = None
        self.warned = set()

    def on_startup(self):
        self.publish_var = self.config("publish_var", default="FRAME_DISTORTION")
        self.frame, why = frame_from_mission(self.global_config("LatOrigin", type=float),
                                             self.global_config("LongOrigin", type=float),
                                             self.config("projection", default="utm").lower())
        if self.frame is None:
            self.report_config_warning(why)
        path = self.config("thresholds_file")
        try:
            limits = load_thresholds(path) if path else load_thresholds()
            self.limits = limits.with_overrides(
                {n: self.config(n) for n in METRICS if self.config(n) is not None})
        except (OSError, ValueError, KeyError) as e:
            self.report_config_warning(f"thresholds: {e}; using the packaged defaults")
            self.limits = load_thresholds()

    def register_variables(self):
        self.register("NAV_X")
        self.register("NAV_Y")

    def on_new_mail(self, mail):
        for msg in mail:
            if msg.name == "NAV_X" and msg.is_double():
                self.x = msg.double()
            elif msg.name == "NAV_Y" and msg.is_double():
                self.y = msg.double()

    def iterate(self):
        if self.frame is None or self.x is None or self.y is None:
            return
        lat, lon = self.frame.to_latlon(self.x, self.y)
        self.last = distortion(self.frame, lat, lon)
        self.notify(self.publish_var, self.last.to_spec())
        over = {name: (val, lim) for name, val, lim in self.limits.exceeded(self.last)}
        for name in set(over) - self.warned:
            self.report_run_warning(f"{name} past its limit {over[name][1]:g}")
        for name in self.warned - set(over):
            self.retract_run_warning(f"{name} past its limit {getattr(self.limits, name):g}")
        self.warned = set(over)

    def build_report(self):
        self.report(f"Frame: {self.frame}" if self.frame else "Frame: none (see config warnings)")
        if self.last is None:
            self.report("Waiting for NAV_X / NAV_Y")
            return True
        t = ACTable(["Metric", "Value", "Limit"])
        for name in METRICS:
            t.add(name, f"{getattr(self.last, name):.4f}", f"{getattr(self.limits, name):g}")
        t.add("range_m", f"{self.last.range_m:.1f}", "")
        self.report(t)
        return True
