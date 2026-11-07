"""
XYCircle — VIEW_CIRCLE geometry DTO.

Spec: x=<v>,y=<v>,radius=<v>[,vertices=<n>][,<common fields>]
"""

from pymoos2.core.strutil import double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject
from pymoos2.dtos.geometry.planar import project_point


class XYCircle(XYObject):
    KIND = "circle"

    def __init__(self, x=None, y=None, radius=None, **kwargs):
        super().__init__(**kwargs)
        if x is not None and y is not None:
            self.x, self.y = float(x), float(y)
            self._set.update(("x", "y"))
        if radius is not None:
            self.radius = float(radius)
            self._set.add("radius")

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.radius = 0.0
        self.vertices = 36
        self._set = set()

    def valid(self):
        return {"x", "y", "radius"} <= self._set and self.radius > 0

    def _set_own_param(self, key, value):
        if value is None:
            return False
        if key in ("x", "y") and is_number(value):
            setattr(self, key, float(value))
            self._set.add(key)
        elif key in ("radius", "rad") and is_number(value):
            self.radius = float(value)
            self._set.add("radius")
        elif key == "vertices" and is_number(value):
            self.vertices = max(3, int(float(value)))
        else:
            return False
        return True

    def points(self, n=None):
        n = n or self.vertices
        return [project_point(360.0 * i / n, self.radius, self.x, self.y) for i in range(n)]

    def get_spec(self, active=None):
        parts = [f"x={double_to_string_x(self.x, 2)}", f"y={double_to_string_x(self.y, 2)}",
                 f"radius={double_to_string_x(self.radius, 2)}"]
        if self.vertices != 36:
            parts.append(f"vertices={self.vertices}")
        return self._join(parts, active)

    def _inactive_parts(self):
        return ["x=0", "y=0", "radius=1"]

    def _fields_dict(self):
        return {"x": self.x, "y": self.y, "radius": self.radius}

    def __repr__(self):
        return f"XYCircle(x={self.x:.1f}, y={self.y:.1f}, r={self.radius:.1f}, label={self.label!r})"
