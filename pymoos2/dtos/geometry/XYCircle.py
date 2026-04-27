"""
XYCircle — VIEW_CIRCLE geometry DTO.

Spec format: x=<val>,y=<val>,radius=<val>[,vertices=<n>][,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYCircle(XYObject):
    def __init__(self, x=0.0, y=0.0, radius=0.0, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y
        self.radius = radius
        self.vertices = 36

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}", f"radius={self.radius:.2f}"]
        if self.vertices != 36:
            parts.append(f"vertices={self.vertices}")
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "x" in params: obj.x = float(params.pop("x"))
        if "y" in params: obj.y = float(params.pop("y"))
        if "radius" in params: obj.radius = float(params.pop("radius"))
        if "vertices" in params: obj.vertices = int(params.pop("vertices"))
        cls._parse_common(obj, params)
        return obj

    def __repr__(self):
        return f"XYCircle(x={self.x:.1f}, y={self.y:.1f}, r={self.radius:.1f}, label={self.label!r})"
