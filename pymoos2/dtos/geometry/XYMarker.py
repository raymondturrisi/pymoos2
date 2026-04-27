"""
XYMarker — VIEW_MARKER geometry DTO.

Spec format: x=<val>,y=<val>,width=<val>[,range=<val>][,type=<type>][,owner=<str>]
             [,primary_color=<c>][,secondary_color=<c>][,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYMarker(XYObject):
    def __init__(self, x=0.0, y=0.0, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y
        self.width = 1.0
        self.range = -1.0
        self.marker_type = ""
        self.owner = ""
        self.primary_color = ""
        self.secondary_color = ""

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}", f"width={self.width}"]
        if self.range >= 0:
            parts.append(f"range={self.range}")
        if self.marker_type:
            parts.append(f"type={self.marker_type}")
        if self.owner:
            parts.append(f"owner={self.owner}")
        if self.primary_color:
            parts.append(f"primary_color={self.primary_color}")
        if self.secondary_color:
            parts.append(f"secondary_color={self.secondary_color}")
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "x" in params: obj.x = float(params.pop("x"))
        if "y" in params: obj.y = float(params.pop("y"))
        if "width" in params: obj.width = float(params.pop("width"))
        if "range" in params: obj.range = float(params.pop("range"))
        if "type" in params: obj.marker_type = params.pop("type")
        if "owner" in params: obj.owner = params.pop("owner")
        if "primary_color" in params: obj.primary_color = params.pop("primary_color")
        if "secondary_color" in params: obj.secondary_color = params.pop("secondary_color")
        cls._parse_common(obj, params)
        return obj
