"""
XYVector — VIEW_VECTOR geometry DTO.

Spec: x=<v>,y=<v>,ang=<deg>,mag=<m>[,head_size=<m>][,<common fields>]
Also accepted: xpos/ypos, and xdot/ydot in place of ang/mag.
"""

import math

from pymoos2.core.strutil import double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject
from pymoos2.dtos.geometry.planar import project_point


class XYVector(XYObject):
    KIND = "vector"

    def __init__(self, x=None, y=None, ang=None, mag=None, **kwargs):
        super().__init__(**kwargs)
        if x is not None and y is not None:
            self.x, self.y = float(x), float(y)
            self._set.update(("x", "y"))
        if ang is not None:
            self.ang = float(ang)
        if mag is not None:
            self.mag = float(mag)

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.ang = 0.0
        self.mag = 0.0
        self.head_size = None
        self._set = set()
        self._xdot = None
        self._ydot = None

    def valid(self):
        return {"x", "y"} <= self._set

    def _set_own_param(self, key, value):
        if value is None or not is_number(value):
            return False
        f = float(value)
        if key in ("x", "xpos"):
            self.x = f
            self._set.add("x")
        elif key in ("y", "ypos"):
            self.y = f
            self._set.add("y")
        elif key == "ang":
            self.ang = f
        elif key == "mag":
            self.mag = f
        elif key == "head_size":
            self.head_size = f
        elif key == "xdot":
            self._xdot = f
            self._merge_dots()
        elif key == "ydot":
            self._ydot = f
            self._merge_dots()
        else:
            return False
        return True

    def _merge_dots(self):
        if self._xdot is not None and self._ydot is not None:
            self.mag = math.hypot(self._xdot, self._ydot)
            self.ang = math.degrees(math.atan2(self._xdot, self._ydot)) % 360.0

    def xdot(self):
        return math.sin(math.radians(self.ang)) * self.mag

    def ydot(self):
        return math.cos(math.radians(self.ang)) * self.mag

    def head(self, length_zoom=1.0):
        """End point of the vector."""
        return project_point(self.ang, self.mag * length_zoom, self.x, self.y)

    def get_spec(self, active=None):
        parts = [f"x={double_to_string_x(self.x, 2)}", f"y={double_to_string_x(self.y, 2)}",
                 f"ang={double_to_string_x(self.ang, 2)}", f"mag={double_to_string_x(self.mag, 2)}"]
        if self.head_size is not None:
            parts.append(f"head_size={double_to_string_x(self.head_size, 1)}")
        return self._join(parts, active)

    def _inactive_parts(self):
        return ["x=0", "y=0"]

    def _fields_dict(self):
        d = {"x": self.x, "y": self.y, "ang": self.ang, "mag": self.mag}
        if self.head_size is not None:
            d["head_size"] = self.head_size
        return d

    def __repr__(self):
        return f"XYVector(x={self.x:.1f}, y={self.y:.1f}, ang={self.ang:.0f}, mag={self.mag:.1f})"
