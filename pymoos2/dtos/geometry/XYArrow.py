"""
XYArrow — VIEW_ARROW geometry DTO.

Spec format: ctrx=<val>,ctry=<val>,ang=<val>,bwid=<val>,blen=<val>,hwid=<val>,hlen=<val>[,<common>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYArrow(XYObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctrx = 0.0
        self.ctry = 0.0
        self.ang = 0.0
        self.bwid = 0.0
        self.blen = 0.0
        self.hwid = 0.0
        self.hlen = 0.0

    def get_spec(self):
        parts = [f"ctrx={self.ctrx:.2f}", f"ctry={self.ctry:.2f}",
                 f"ang={self.ang:.2f}", f"bwid={self.bwid:.2f}",
                 f"blen={self.blen:.2f}", f"hwid={self.hwid:.2f}",
                 f"hlen={self.hlen:.2f}"]
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        for field in ("ctrx", "ctry", "ang", "bwid", "blen", "hwid", "hlen"):
            if field in params:
                setattr(obj, field, float(params.pop(field)))
        cls._parse_common(obj, params)
        return obj
