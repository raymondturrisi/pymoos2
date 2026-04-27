"""
XYCommsPulse — VIEW_COMMS_PULSE geometry DTO.

Spec format: sx=<val>,sy=<val>,tx=<val>,ty=<val>,beam_width=<val>,fill=<val>
             [,ptype=<type>][,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYCommsPulse(XYObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sx = 0.0
        self.sy = 0.0
        self.tx = 0.0
        self.ty = 0.0
        self.beam_width = 10.0
        self.fill = 0.5
        self.ptype = ""

    def get_spec(self):
        parts = [f"sx={self.sx:.2f}", f"sy={self.sy:.2f}",
                 f"tx={self.tx:.2f}", f"ty={self.ty:.2f}",
                 f"beam_width={self.beam_width}", f"fill={self.fill}"]
        if self.ptype:
            parts.append(f"ptype={self.ptype}")
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        for field in ("sx", "sy", "tx", "ty", "beam_width", "fill"):
            if field in params:
                setattr(obj, field, float(params.pop(field)))
        if "ptype" in params: obj.ptype = params.pop("ptype")
        cls._parse_common(obj, params)
        return obj
