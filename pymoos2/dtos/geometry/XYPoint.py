"""
XYPoint — VIEW_POINT geometry DTO.

Spec format: x=<val>,y=<val>[,z=<val>][,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYPoint(XYObject):
    def __init__(self, x=0.0, y=0.0, z=0.0, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y
        self.z = z

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}"]
        if self.z != 0.0:
            parts.append(f"z={self.z:.2f}")
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "x" in params: obj.x = float(params.pop("x"))
        if "y" in params: obj.y = float(params.pop("y"))
        if "z" in params: obj.z = float(params.pop("z"))
        if "type" in params: params.pop("type")
        cls._parse_common(obj, params)
        return obj

    def __repr__(self):
        return f"XYPoint(x={self.x:.1f}, y={self.y:.1f}, label={self.label!r})"
