"""
XYOval — VIEW_OVAL geometry DTO.

Spec format: x=<val>,y=<val>,rad=<val>,len=<val>,ang=<val>,draw_degs=<val>
             [,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYOval(XYObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.x = 0.0
        self.y = 0.0
        self.rad = 0.0
        self.length = 0.0
        self.ang = 0.0
        self.draw_degs = 5.0

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}",
                 f"rad={self.rad:.2f}", f"len={self.length:.2f}",
                 f"ang={self.ang:.2f}", f"draw_degs={self.draw_degs}"]
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "x" in params: obj.x = float(params.pop("x"))
        if "y" in params: obj.y = float(params.pop("y"))
        if "rad" in params: obj.rad = float(params.pop("rad"))
        if "len" in params: obj.length = float(params.pop("len"))
        if "ang" in params: obj.ang = float(params.pop("ang"))
        if "draw_degs" in params: obj.draw_degs = float(params.pop("draw_degs"))
        cls._parse_common(obj, params)
        return obj
