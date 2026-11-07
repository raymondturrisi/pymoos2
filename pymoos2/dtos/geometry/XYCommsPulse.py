"""XYCommsPulse — VIEW_COMMS_PULSE geometry DTO: a fading beam from a source to a target.

Spec: sx=<v>,sy=<v>,tx=<v>,ty=<v>[,beam_width=<m>][,duration=<s>][,fill=<0..1>]
      [,ptype=<s>][,<common fields>]
Defaults: beam_width 10, duration 3, fill 0.35.
"""

from pymoos2.core.strutil import double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject
from pymoos2.dtos.geometry.planar import rel_ang, project_point

DEFAULT_DURATION = 3.0


class XYCommsPulse(XYObject):
    KIND = "comms_pulse"

    def _init_fields(self):
        self.sx = 0.0
        self.sy = 0.0
        self.tx = 0.0
        self.ty = 0.0
        self.beam_width = 10.0
        self.fill = 0.35
        self.ptype = ""
        self._set = set()

    def valid(self):
        return {"sx", "sy", "tx", "ty"} <= self._set

    def effective_duration(self):
        return self.duration if self.duration is not None and self.duration >= 0 else DEFAULT_DURATION

    def triangle(self):
        """Source vertex plus two target vertices offset by half the beam width."""
        ang = rel_ang(self.sx, self.sy, self.tx, self.ty)
        a = project_point(ang + 90, self.beam_width / 2.0, self.tx, self.ty)
        b = project_point(ang - 90, self.beam_width / 2.0, self.tx, self.ty)
        return [(self.sx, self.sy), a, b]

    def fill_at(self, now):
        if self.time is None:
            return self.fill
        d = self.effective_duration()
        return self.fill * max(0.0, 1.0 - max(0.0, now - self.time) / d) if d > 0 else 0.0

    def finished(self, now):
        return self.time is not None and (now - self.time) > self.effective_duration()

    def _set_own_param(self, key, value):
        if value is None:
            return False
        if key in ("sx", "sy", "tx", "ty", "beam_width", "fill"):
            if not is_number(value):
                return True
            setattr(self, key, float(value))
            if key in ("sx", "sy", "tx", "ty"):
                self._set.add(key)
        elif key == "ptype":
            self.ptype = value
        else:
            return False
        return True

    def get_spec(self, active=None):
        parts = [f"sx={double_to_string_x(self.sx, 2)}", f"sy={double_to_string_x(self.sy, 2)}",
                 f"tx={double_to_string_x(self.tx, 2)}", f"ty={double_to_string_x(self.ty, 2)}",
                 f"beam_width={double_to_string_x(self.beam_width, 2)}",
                 f"fill={double_to_string_x(self.fill, 2)}"]
        if self.ptype:
            parts.append(f"ptype={self.ptype}")
        return self._join(parts, active)

    def _fields_dict(self):
        return {"sx": self.sx, "sy": self.sy, "tx": self.tx, "ty": self.ty,
                "beam_width": self.beam_width, "fill": self.fill, "ptype": self.ptype,
                "effective_duration": self.effective_duration()}
