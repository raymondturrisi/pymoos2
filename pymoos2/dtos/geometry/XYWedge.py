"""
XYWedge — VIEW_WEDGE geometry DTO: an annular sector.

Spec: x=<v>,y=<v>,rad_low=<m>,rad_hgh=<m>,ang_low=<deg>,ang_hgh=<deg>[,<common fields>]
"""

from pymoos2.core.strutil import double_to_string, double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject
from pymoos2.dtos.geometry.planar import project_point


class XYWedge(XYObject):
    KIND = "wedge"

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.rad_low = 0.0
        self.rad_hgh = 0.0
        self.ang_low = 0.0
        self.ang_hgh = 0.0
        self._set = set()

    def valid(self):
        return {"x", "y"} <= self._set and self.rad_hgh > 0

    def outline(self, step_deg=5.0):
        """Closed outline: outer arc low->high, then inner arc high->low."""
        lo, hi = self.ang_low % 360.0, self.ang_hgh % 360.0
        if hi <= lo:
            hi += 360.0
        angs = []
        a = lo
        while a < hi:
            angs.append(a)
            a += step_deg
        angs.append(hi)
        outer = [project_point(a, self.rad_hgh, self.x, self.y) for a in angs]
        inner = [project_point(a, self.rad_low, self.x, self.y) for a in reversed(angs)]
        if self.rad_low <= 0:
            inner = [(self.x, self.y)]
        return outer + inner

    def _set_own_param(self, key, value):
        if value is None or not is_number(value):
            return False
        if key in ("x", "y", "rad_low", "rad_hgh", "ang_low", "ang_hgh"):
            setattr(self, key, float(value))
            if key in ("x", "y"):
                self._set.add(key)
            return True
        return False

    def get_spec(self, active=None):
        parts = [f"x={double_to_string(self.x, 2)}", f"y={double_to_string(self.y, 2)}",
                 f"rad_low={double_to_string_x(self.rad_low, 2)}", f"rad_hgh={double_to_string_x(self.rad_hgh, 2)}",
                 f"ang_low={double_to_string_x(self.ang_low, 2)}", f"ang_hgh={double_to_string_x(self.ang_hgh, 2)}"]
        return self._join(parts, active)

    def _inactive_parts(self):
        return ["x=0", "y=0"]

    def _fields_dict(self):
        return {"x": self.x, "y": self.y, "rad_low": self.rad_low, "rad_hgh": self.rad_hgh,
                "ang_low": self.ang_low, "ang_hgh": self.ang_hgh}
