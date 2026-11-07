"""
XYPoint — VIEW_POINT geometry DTO.

Spec: x=<v>,y=<v>[,z=<v>][,trans=<0..1>][,<common fields>]
Also accepted: "3,4", "3:4" and the abbreviated "4,5:label,foo:source,bravo".
"""

from pymoos2.core.strutil import double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject, tokenize_spec


class XYPoint(XYObject):
    KIND = "point"
    SDIGITS = 2

    def __init__(self, x=None, y=None, z=0.0, **kwargs):
        super().__init__(**kwargs)
        if x is not None:
            self.x = float(x)
            self._set.add("x")
        if y is not None:
            self.y = float(y)
            self._set.add("y")
        self.z = float(z)

    def _init_fields(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.trans = 0.0
        self._set = set()

    def set_xy(self, x, y):
        self.x, self.y = float(x), float(y)
        self._set.update(("x", "y"))

    def valid(self):
        return "x" in self._set and "y" in self._set

    def _set_own_param(self, key, value):
        if value is None or not is_number(value):
            return key in ("heading", "hdg")
        if key in ("x", "y", "z", "trans"):
            setattr(self, key, float(value))
            self._set.add(key)
        elif key in ("shiftx", "shifty", "shiftz"):
            attr = key[-1]
            setattr(self, attr, getattr(self, attr) + float(value))
        elif key in ("heading", "hdg"):
            pass
        else:
            return False
        return True

    @classmethod
    def from_spec(cls, spec):
        s = spec.strip()
        if "=" not in s:
            sep = "," if "," in s else ":"
            parts = [p.strip() for p in s.split(sep)]
            if len(parts) == 2 and all(is_number(p) for p in parts):
                return cls(float(parts[0]), float(parts[1]))
        if "=" not in s and ":" in s:
            obj = cls()
            for i, item in enumerate(s.split(":")):
                fields = [f.strip() for f in item.split(",")]
                if i == 0 and len(fields) >= 2 and is_number(fields[0]) and is_number(fields[1]):
                    obj.set_xy(float(fields[0]), float(fields[1]))
                    if len(fields) >= 3 and is_number(fields[2]):
                        obj.z = float(fields[2])
                elif len(fields) >= 2:
                    if not obj.set_param(fields[0], ",".join(fields[1:])):
                        obj.extra[fields[0].lower()] = ",".join(fields[1:])
            return obj
        obj = cls()
        obj._apply_tokens(tokenize_spec(s))
        return obj

    def get_spec(self, active=None):
        parts = [f"x={double_to_string_x(self.x, self.SDIGITS)}",
                 f"y={double_to_string_x(self.y, self.SDIGITS)}"]
        if self.z != 0:
            parts.append(f"z={double_to_string_x(self.z, self.SDIGITS)}")
        if self.trans != 0:
            parts.append(f"trans={double_to_string_x(self.trans, 2)}")
        return self._join(parts, active)

    def _inactive_parts(self):
        return ["x=0", "y=0"]

    def _fields_dict(self):
        d = {"x": self.x, "y": self.y}
        if self.z:
            d["z"] = self.z
        if self.trans:
            d["trans"] = self.trans
        return d

    def __repr__(self):
        return f"XYPoint(x={self.x:.1f}, y={self.y:.1f}, label={self.label!r})"
