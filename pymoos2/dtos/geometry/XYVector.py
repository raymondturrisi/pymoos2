"""
XYVector — VIEW_VECTOR geometry DTO.

Spec format: x=<val>,y=<val>,ang=<val>,mag=<val>[,head_size=<val>][,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYVector(XYObject):
    def __init__(self, x=0.0, y=0.0, ang=0.0, mag=0.0, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y
        self.ang = ang
        self.mag = mag
        self.head_size = -1.0

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}",
                 f"ang={self.ang:.2f}", f"mag={self.mag:.2f}"]
        if self.head_size >= 0:
            parts.append(f"head_size={self.head_size}")
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "x" in params: obj.x = float(params.pop("x"))
        if "y" in params: obj.y = float(params.pop("y"))
        if "ang" in params: obj.ang = float(params.pop("ang"))
        if "mag" in params: obj.mag = float(params.pop("mag"))
        if "head_size" in params: obj.head_size = float(params.pop("head_size"))
        cls._parse_common(obj, params)
        return obj

    def __repr__(self):
        return f"XYVector(x={self.x:.1f}, y={self.y:.1f}, ang={self.ang:.0f}, mag={self.mag:.1f})"
