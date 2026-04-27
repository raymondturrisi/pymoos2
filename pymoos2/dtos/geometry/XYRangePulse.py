"""
XYRangePulse — VIEW_RANGE_PULSE geometry DTO.

Spec format: x=<val>,y=<val>,radius=<val>,fill=<val>[,linger=<val>]
             [,fill_invariant=<bool>][,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYRangePulse(XYObject):
    def __init__(self, x=0.0, y=0.0, radius=0.0, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y
        self.radius = radius
        self.fill = 0.5
        self.linger = -1.0
        self.fill_invariant = False

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}",
                 f"radius={self.radius:.2f}", f"fill={self.fill}"]
        if self.linger >= 0:
            parts.append(f"linger={self.linger}")
        if self.fill_invariant:
            parts.append("fill_invariant=true")
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "x" in params: obj.x = float(params.pop("x"))
        if "y" in params: obj.y = float(params.pop("y"))
        if "radius" in params: obj.radius = float(params.pop("radius"))
        if "fill" in params: obj.fill = float(params.pop("fill"))
        if "linger" in params: obj.linger = float(params.pop("linger"))
        if "fill_invariant" in params:
            obj.fill_invariant = params.pop("fill_invariant").lower() == "true"
        cls._parse_common(obj, params)
        return obj
