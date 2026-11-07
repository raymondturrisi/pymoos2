"""
XYMarker — VIEW_MARKER geometry DTO.

Spec: x=<v>,y=<v>[,width=<m>][,range=<m>][,type=<t>][,owner=<s>]
      [,primary_color=<c>][,secondary_color=<c>][,<common fields>]
Aliases: xpos/ypos, scale (=width), color (=primary_color), colors=p:s.
Types: circle (default), square, diamond, efield, gateway, triangle, kelp.
"""

from pymoos2.core.strutil import double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject
from pymoos2.dtos.geometry.colors import is_color

MARKER_TYPES = ("circle", "square", "diamond", "efield", "gateway", "triangle", "kelp")


class XYMarker(XYObject):
    KIND = "marker"

    def __init__(self, x=None, y=None, **kwargs):
        super().__init__(**kwargs)
        if x is not None and y is not None:
            self.x, self.y = float(x), float(y)
            self._set.update(("x", "y"))

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.width = 5.0
        self.range = None
        self.marker_type = "circle"
        self.owner = ""
        self.primary_color = ""
        self.secondary_color = ""
        self._set = set()

    def valid(self):
        return {"x", "y"} <= self._set

    def _set_own_param(self, key, value):
        if value is None:
            return False
        if key in ("x", "xpos") and is_number(value):
            self.x = float(value)
            self._set.add("x")
        elif key in ("y", "ypos") and is_number(value):
            self.y = float(value)
            self._set.add("y")
        elif key in ("width", "scale") and is_number(value):
            self.width = float(value)
        elif key == "range" and is_number(value):
            self.range = float(value)
        elif key == "type":
            if value.lower() in MARKER_TYPES:
                self.marker_type = value.lower()
            self.type = value
        elif key == "owner":
            self.owner = value
        elif key in ("primary_color", "color"):
            if is_color(value):
                self.primary_color = value
        elif key == "secondary_color":
            if is_color(value):
                self.secondary_color = value
        elif key == "colors":
            parts = value.split(":")
            if parts and is_color(parts[0]):
                self.primary_color = parts[0]
            if len(parts) > 1 and is_color(parts[1]):
                self.secondary_color = parts[1]
        else:
            return False
        return True

    def get_spec(self, active=None):
        parts = [f"x={double_to_string_x(self.x, 2)}", f"y={double_to_string_x(self.y, 2)}",
                 f"width={double_to_string_x(self.width, 2)}"]
        if self.range is not None:
            parts.append(f"range={double_to_string_x(self.range, 2)}")
        if self.marker_type:
            parts.append(f"type={self.marker_type}")
        if self.owner:
            parts.append(f"owner={self.owner}")
        if self.primary_color:
            parts.append(f"primary_color={self.primary_color}")
        if self.secondary_color:
            parts.append(f"secondary_color={self.secondary_color}")
        common = [p for p in self._common_spec(active) if not p.startswith("type=")]
        return ",".join(parts + common)

    def _inactive_parts(self):
        return ["x=0", "y=0"]

    def _fields_dict(self):
        d = {"x": self.x, "y": self.y, "width": self.width, "marker_type": self.marker_type}
        if self.owner:
            d["owner"] = self.owner
        if self.range is not None:
            d["range"] = self.range
        if self.primary_color:
            d["primary_color"] = self.primary_color
        if self.secondary_color:
            d["secondary_color"] = self.secondary_color
        return d
