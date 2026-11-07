"""XYRangePulse — VIEW_RANGE_PULSE geometry DTO: an expanding ring.

Spec: x=<v>,y=<v>[,radius=<m>][,duration=<s>][,linger=<s>][,fill=<0..1>]
      [,fill_invariant=<bool>][,<common fields>]
Defaults: radius 40, duration 15, fill 0.25, linger 0.
"""

from pymoos2.core.strutil import double_to_string_x, is_number, to_bool
from pymoos2.dtos.geometry.XYObject import XYObject

DEFAULT_DURATION = 15.0


class XYRangePulse(XYObject):
    KIND = "range_pulse"

    def __init__(self, x=None, y=None, radius=None, **kwargs):
        super().__init__(**kwargs)
        if x is not None and y is not None:
            self.x, self.y = float(x), float(y)
            self._set.update(("x", "y"))
        if radius is not None:
            self.radius = float(radius)

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.radius = 40.0
        self.fill = 0.25
        self.linger = 0.0
        self.fill_invariant = False
        self._set = set()

    def valid(self):
        return {"x", "y"} <= self._set

    def effective_duration(self):
        return self.duration if self.duration is not None and self.duration >= 0 else DEFAULT_DURATION

    def radius_at(self, now):
        """Ring radius at MOOS time now (grows linearly over the duration)."""
        if self.time is None:
            return self.radius
        elapsed = now - self.time
        if elapsed < 0:
            return 0.0
        pct = min(1.0, elapsed / self.effective_duration()) if self.effective_duration() > 0 else 1.0
        return self.radius * pct

    def fill_at(self, now):
        if self.fill_invariant or self.time is None:
            return self.fill
        elapsed = max(0.0, now - self.time)
        d = self.effective_duration()
        return self.fill * max(0.0, 1.0 - elapsed / d) if d > 0 else 0.0

    def finished(self, now):
        """True once duration plus linger has passed."""
        if self.time is None:
            return False
        return (now - self.time) > self.effective_duration() + self.linger

    def _set_own_param(self, key, value):
        if value is None:
            return False
        if key in ("x", "y") and is_number(value):
            setattr(self, key, float(value))
            self._set.add(key)
        elif key in ("radius", "rad") and is_number(value):
            self.radius = float(value)
        elif key == "fill" and is_number(value):
            self.fill = float(value)
        elif key == "linger" and is_number(value):
            self.linger = float(value)
        elif key == "fill_invariant":
            self.fill_invariant = to_bool(value)
        else:
            return False
        return True

    def get_spec(self, active=None):
        parts = [f"x={double_to_string_x(self.x, 2)}", f"y={double_to_string_x(self.y, 2)}",
                 f"radius={double_to_string_x(self.radius, 2)}", f"fill={double_to_string_x(self.fill, 2)}"]
        if self.linger:
            parts.append(f"linger={double_to_string_x(self.linger, 2)}")
        if self.fill_invariant:
            parts.append("fill_invariant=true")
        return self._join(parts, active)

    def _inactive_parts(self):
        return ["x=0", "y=0"]

    def _fields_dict(self):
        return {"x": self.x, "y": self.y, "radius": self.radius, "fill": self.fill,
                "linger": self.linger, "fill_invariant": self.fill_invariant,
                "effective_duration": self.effective_duration()}
