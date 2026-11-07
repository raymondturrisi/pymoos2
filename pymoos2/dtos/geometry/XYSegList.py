"""
XYSegList — VIEW_SEGLIST geometry DTO.

Spec: pts={x,y[,z[,prop]]:x,y:...}[,tags={i:j:tag#i:j:tag}][,<common fields>]
Also accepted: pts={x=1,y=2:x=3,y=4}, the abbreviated "pts:x,y:x,y:label,foo"
and bare "x,y:x,y:label,foo" forms.
"""

import math

from pymoos2.core.strutil import double_to_string_x, is_number, parse_string_z
from pymoos2.dtos.geometry.XYObject import XYObject, tokenize_spec


def _snap(v, step):
    if step <= 0:
        return v
    return round(v / step) * step


class XYSegList(XYObject):
    KIND = "seglist"
    DEFAULT_PRECISION = 1

    def _init_fields(self):
        self.vx = []
        self.vy = []
        self.vz = []
        self.vprop = []
        self.edge_tags = []
        self.unsupported_format = ""

    def add_vertex(self, x, y, z=0.0, prop=""):
        self.vx.append(float(x))
        self.vy.append(float(y))
        self.vz.append(float(z))
        self.vprop.append(prop)

    def clear(self):
        self._init_fields()

    def size(self):
        return len(self.vx)

    def vertices(self):
        return list(zip(self.vx, self.vy))

    def length(self):
        total = 0.0
        for i in range(1, len(self.vx)):
            total += math.hypot(self.vx[i] - self.vx[i - 1], self.vy[i] - self.vy[i - 1])
        return total

    def centroid(self):
        n = len(self.vx)
        if n == 0:
            return None
        return sum(self.vx) / n, sum(self.vy) / n

    def bounds(self):
        if not self.vx:
            return None
        return min(self.vx), min(self.vy), max(self.vx), max(self.vy)

    def apply_snap(self, step):
        if step and step > 0:
            self.vx = [_snap(v, step) for v in self.vx]
            self.vy = [_snap(v, step) for v in self.vy]

    def add_edge_tag(self, i, j, tag):
        if abs(int(i) - int(j)) != 1:
            return False
        self.edge_tags.append((int(i), int(j), tag))
        return True

    def valid(self):
        return (self.size() > 0 or not self.active) and not self.unsupported_format

    def get_spec_pts(self, precision=None):
        p = min(6, self.DEFAULT_PRECISION if precision is None else int(precision))
        if not self.vx:
            return ""
        items = []
        for i in range(len(self.vx)):
            s = double_to_string_x(self.vx[i], p) + "," + double_to_string_x(self.vy[i], p)
            if self.vz[i] != 0 or self.vprop[i]:
                s += "," + double_to_string_x(self.vz[i], p)
            if self.vprop[i]:
                s += "," + self.vprop[i]
            items.append(s)
        return "pts={" + ":".join(items) + "}"

    def get_spec_tags(self):
        if not self.edge_tags:
            return ""
        return "tags={" + "#".join(f"{i}:{j}:{t}" for i, j, t in self.edge_tags) + "}"

    def _own_parts(self, precision):
        parts = []
        pts = self.get_spec_pts(precision)
        if pts:
            parts.append(pts)
        tags = self.get_spec_tags()
        if tags:
            parts.append(tags)
        return parts

    def get_spec(self, precision=None, active=None):
        return self._join(self._own_parts(precision), active)

    def _inactive_parts(self):
        return ["pts={0,0:9,0:0,9}"]

    def _fields_dict(self):
        d = {"pts": [[x, y, z] for x, y, z in zip(self.vx, self.vy, self.vz)]}
        if any(self.vprop):
            d["props"] = list(self.vprop)
        if self.edge_tags:
            d["tags"] = [list(t) for t in self.edge_tags]
        return d

    def _parse_pts(self, body):
        """Parse the inside of pts={...}: x,y[,z[,prop]] or x=..,y=.. items separated by ':'."""
        for item in body.split(":"):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                kv = {}
                for tok in item.split(","):
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        kv[k.strip().lower()] = v.strip()
                if "x" in kv and "y" in kv and is_number(kv["x"]) and is_number(kv["y"]):
                    self.add_vertex(float(kv["x"]), float(kv["y"]),
                                    float(kv["z"]) if is_number(kv.get("z", "")) else 0.0)
                continue
            fields = [f.strip() for f in item.split(",")]
            if len(fields) < 2 or not is_number(fields[0]) or not is_number(fields[1]):
                continue
            z = 0.0
            prop = ""
            if len(fields) >= 3:
                if is_number(fields[2]):
                    z = float(fields[2])
                    if len(fields) >= 4:
                        prop = fields[3]
                else:
                    prop = fields[2]
            self.add_vertex(float(fields[0]), float(fields[1]), z, prop)

    def _parse_tags(self, body):
        for item in body.split("#"):
            parts = item.split(":", 2)
            if len(parts) == 3 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                self.add_edge_tag(int(parts[0]), int(parts[1]), parts[2])

    def _set_own_param(self, key, value):
        if value is None:
            return False
        if key == "pts" or key == "points":
            inner = value.strip()
            if inner.startswith("{") and inner.endswith("}"):
                inner = inner[1:-1]
            self._parse_pts(inner)
            return True
        if key == "tags":
            inner = value.strip()
            if inner.startswith("{") and inner.endswith("}"):
                inner = inner[1:-1]
            self._parse_tags(inner)
            return True
        if key == "format":
            self.unsupported_format = value.lower()
            return True
        if key == "snap":
            if is_number(value):
                self._pending_snap = float(value)
            return True
        return False

    def _parse_abbreviated(self, spec):
        """'x,y:x,y:label,foo:source,alpha' (colon separated items)."""
        for item in spec.split(":"):
            item = item.strip()
            if not item:
                continue
            fields = [f.strip() for f in item.split(",")]
            if len(fields) >= 2 and is_number(fields[0]) and is_number(fields[1]):
                z = float(fields[2]) if len(fields) >= 3 and is_number(fields[2]) else 0.0
                self.add_vertex(float(fields[0]), float(fields[1]), z)
            elif len(fields) >= 2:
                if not self.set_param(fields[0], ",".join(fields[1:])):
                    self.extra[fields[0].lower()] = ",".join(fields[1:])

    @classmethod
    def from_spec(cls, spec):
        obj = cls()
        s = spec.strip()
        low = s.lower()
        if low.startswith("pts:"):
            obj._parse_abbreviated(s[4:])
            return obj
        if low.startswith("points:"):
            obj._parse_abbreviated(s[7:])
            return obj
        if "=" not in s and ":" in s:
            obj._parse_abbreviated(s)
            return obj
        obj._pending_snap = 0.0
        obj._apply_tokens(tokenize_spec(s))
        obj.apply_snap(obj._pending_snap)
        del obj._pending_snap
        return obj

    def __repr__(self):
        return f"{type(self).__name__}({self.size()} pts, label={self.label!r})"
