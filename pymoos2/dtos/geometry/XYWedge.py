"""
XYWedge — VIEW_WEDGE geometry DTO.

Spec format: x=<val>,y=<val>,rad_low=<val>,rad_hgh=<val>,ang_low=<val>,ang_hgh=<val>
             [,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYWedge(XYObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.x = 0.0
        self.y = 0.0
        self.rad_low = 0.0
        self.rad_hgh = 0.0
        self.ang_low = 0.0
        self.ang_hgh = 0.0

    def get_spec(self):
        parts = [f"x={self.x:.2f}", f"y={self.y:.2f}",
                 f"rad_low={self.rad_low:.2f}", f"rad_hgh={self.rad_hgh:.2f}",
                 f"ang_low={self.ang_low:.2f}", f"ang_hgh={self.ang_hgh:.2f}"]
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        for field in ("x", "y", "rad_low", "rad_hgh", "ang_low", "ang_hgh"):
            if field in params:
                setattr(obj, field, float(params.pop(field)))
        cls._parse_common(obj, params)
        return obj
