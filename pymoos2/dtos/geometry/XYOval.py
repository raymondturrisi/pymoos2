"""
XYOval — VIEW_OVAL geometry DTO: a stadium shape (two semicircles of radius
rad whose centers are len apart along heading ang, joined by straight sides).

Spec: x=<v>,y=<v>,rad=<m>,len=<m>,ang=<deg>[,draw_degs=<2|5|10|15>][,<common fields>]
"""

from pymoos2.core.strutil import double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject
from pymoos2.dtos.geometry.planar import project_point


class XYOval(XYObject):
    KIND = "oval"

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.rad = 0.0
        self.length = 0.0
        self.ang = 0.0
        self.draw_degs = 5.0
        self._set = set()

    def valid(self):
        return {"x", "y", "ang"} <= self._set and self.rad > 0

    def end_centers(self):
        c1 = project_point(self.ang, self.length / 2.0, self.x, self.y)
        c2 = project_point(self.ang + 180, self.length / 2.0, self.x, self.y)
        return c1, c2

    def vertices(self):
        degs = self.draw_degs if self.draw_degs in (2, 5, 10, 15) else 5.0
        c1, c2 = self.end_centers()
        pts = []
        d = -90.0
        while d <= 90.0:
            pts.append(project_point(self.ang + d, self.rad, *c1))
            d += degs
        d = -90.0
        while d <= 90.0:
            pts.append(project_point(self.ang + 180 + d, self.rad, *c2))
            d += degs
        return pts

    def _set_own_param(self, key, value):
        if value is None or not is_number(value):
            return False
        f = float(value)
        if key in ("x", "y", "ang"):
            setattr(self, key, f)
            self._set.add(key)
        elif key in ("rad", "radius"):
            self.rad = f
        elif key in ("len", "length"):
            self.length = f
        elif key == "draw_degs":
            self.draw_degs = f
        else:
            return False
        return True

    def get_spec(self, *, active=None):
        parts = [f"x={double_to_string_x(self.x, 2)}", f"y={double_to_string_x(self.y, 2)}",
                 f"rad={double_to_string_x(self.rad, 2)}", f"len={double_to_string_x(self.length, 2)}",
                 f"ang={double_to_string_x(self.ang, 2)}", f"draw_degs={double_to_string_x(self.draw_degs, 1)}"]
        return self._join(parts, active)

    def _inactive_parts(self):
        return ["x=0", "y=0"]

    def _fields_dict(self):
        return {"x": self.x, "y": self.y, "rad": self.rad, "len": self.length, "ang": self.ang}
