"""XYPolygon — VIEW_POLYGON geometry DTO.

Accepts pts={...}, the format= constructors (radial, ellipse,
wedge/piewedge, rangewedge, pylon, oval) and their prefix forms, and
"x,y:x,y:label,foo". Non-convex polygons are kept; see is_convex().
"""

import math

from pymoos2.core.strutil import is_number
from pymoos2.dtos.geometry.XYSegList import XYSegList
from pymoos2.dtos.geometry.XYObject import tokenize_spec
from pymoos2.dtos.geometry.planar import rel_ang, project_point


def _angle360(deg):
    deg = math.fmod(deg, 360.0)
    return deg + 360.0 if deg < 0 else deg


class XYPolygon(XYSegList):
    KIND = "polygon"

    def _init_fields(self):
        super()._init_fields()
        self.format = ""

    def area(self):
        n = len(self.vx)
        if n < 3:
            return 0.0
        a = 0.0
        for i in range(n):
            j = (i + 1) % n
            a += self.vx[i] * self.vy[j] - self.vx[j] * self.vy[i]
        return abs(a) / 2.0

    def perimeter(self):
        n = len(self.vx)
        if n < 2:
            return 0.0
        return self.length() + math.hypot(self.vx[0] - self.vx[-1], self.vy[0] - self.vy[-1])

    def is_convex(self):
        n = len(self.vx)
        if n < 3:
            return False
        sign = 0
        for i in range(n):
            x0, y0 = self.vx[i], self.vy[i]
            x1, y1 = self.vx[(i + 1) % n], self.vy[(i + 1) % n]
            x2, y2 = self.vx[(i + 2) % n], self.vy[(i + 2) % n]
            cross = (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)
            if cross != 0:
                s = 1 if cross > 0 else -1
                if sign == 0:
                    sign = s
                elif s != sign:
                    return False
        return True

    def contains(self, px, py):
        """Point-in-polygon by ray casting; works for any simple polygon."""
        n = len(self.vx)
        if n < 3:
            return False
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi, xj, yj = self.vx[i], self.vy[i], self.vx[j], self.vy[j]
            if (yi > py) != (yj > py):
                x_cross = (xj - xi) * (py - yi) / (yj - yi) + xi
                if px < x_cross:
                    inside = not inside
            j = i
        return inside

    def _fields_dict(self):
        d = super()._fields_dict()
        d["convex"] = self.is_convex()
        return d

    @staticmethod
    def radial(x, y, radius, pts, z=0.0, snap=0.0):
        poly = XYPolygon()
        poly.format = "radial"
        delta = 360.0 / pts
        deg = delta / 2.0
        while deg < 360.0:
            nx, ny = project_point(deg, radius, x, y)
            poly.add_vertex(nx, ny, z)
            deg += delta
        poly.apply_snap(snap)
        return poly

    @staticmethod
    def ellipse(x, y, major, minor, pts, degs=None, rads=None, z=0.0, snap=0.0):
        poly = XYPolygon()
        poly.format = "ellipse"
        r = rads if rads is not None else math.radians(degs or 0.0)
        delta = 2 * math.pi / pts
        for i in range(pts):
            a = -math.pi + i * delta
            nx = x + (major / 2 * math.cos(a) * math.cos(r)) - (minor / 2 * math.sin(a) * math.sin(r))
            ny = y + (minor / 2 * math.sin(a) * math.cos(r)) + (major / 2 * math.cos(a) * math.sin(r))
            poly.add_vertex(nx, ny, z)
        poly.apply_snap(snap)
        return poly

    @staticmethod
    def pie_wedge(x, y, lang, rang, rng, pts=0, snap=0.0):
        poly = XYPolygon()
        poly.format = "wedge"
        lang = _angle360(lang)
        rang = _angle360(rang)
        if rang < lang:
            rang += 360.0
        delta = (rang - lang) / pts if (pts > 0 and rang > lang) else (rang - lang)
        poly.add_vertex(x, y)
        poly.add_vertex(*project_point(lang, rng, x, y))
        ang = lang
        while ang < rang and delta > 0:
            ang = min(ang + delta, rang)
            poly.add_vertex(*project_point(ang, rng, x, y))
        poly.apply_snap(snap)
        return poly

    @staticmethod
    def range_wedge(x, y, lang, rang, range_min, range_max, pts=0, snap=0.0):
        poly = XYPolygon()
        poly.format = "rangewedge"
        lang = _angle360(lang)
        rang = _angle360(rang)
        if rang < lang:
            rang += 360.0
        delta = (rang - lang) / pts if (pts > 0 and rang > lang) else (rang - lang)
        poly.add_vertex(*project_point(lang, range_max, x, y))
        ang = lang
        while ang < rang and delta > 0:
            ang = min(ang + delta, rang)
            poly.add_vertex(*project_point(ang, range_max, x, y))
        poly.add_vertex(*project_point(rang, range_min, x, y))
        ang = rang
        while ang > lang and delta > 0:
            ang = max(ang - delta, lang)
            poly.add_vertex(*project_point(ang, range_min, x, y))
        poly.apply_snap(snap)
        return poly

    @staticmethod
    def pylon(x1, y1, x2, y2, axis_pad, perp_pad, z=0.0, snap=0.0):
        poly = XYPolygon()
        poly.format = "pylon"
        ang = rel_ang(x1, y1, x2, y2)
        px, py = project_point(ang - 180, axis_pad, x1, y1)
        poly.add_vertex(*project_point(ang - 90, perp_pad, px, py), z)
        px, py = project_point(ang - 180, axis_pad, x1, y1)
        poly.add_vertex(*project_point(ang + 90, perp_pad, px, py), z)
        px, py = project_point(ang, axis_pad, x2, y2)
        poly.add_vertex(*project_point(ang + 90, perp_pad, px, py), z)
        px, py = project_point(ang, axis_pad, x2, y2)
        poly.add_vertex(*project_point(ang - 90, perp_pad, px, py), z)
        poly.apply_snap(snap)
        return poly

    @staticmethod
    def oval(x, y, rad, length, ang, draw_degs=5.0, snap=0.0):
        from pymoos2.dtos.geometry.XYOval import XYOval
        poly = XYPolygon()
        poly.format = "oval"
        ov = XYOval(x=x, y=y, rad=rad, length=length, ang=ang, draw_degs=draw_degs)
        for vx, vy in ov.vertices():
            poly.add_vertex(vx, vy)
        poly.apply_snap(snap)
        return poly

    @classmethod
    def _from_format(cls, fmt, tokens):
        """Build from a format= spec. Returns None when required fields are missing."""
        kv = {}
        common = []
        for k, v in tokens:
            if k == "snap_value":
                k = "snap"
            if k in ("format", "x", "y", "z", "radius", "pts", "snap", "shiftx", "shifty",
                     "major", "minor", "degs", "rads", "lang", "rang", "range",
                     "range_min", "range_max", "x1", "y1", "x2", "y2", "axis_pad",
                     "perp_pad", "rad", "len", "length", "ang", "draw_degs"):
                kv[k] = v
            else:
                common.append((k, v))

        def num(key, default=None):
            v = kv.get(key)
            return float(v) if v is not None and is_number(v) else default

        snap = num("snap", 0.0) or 0.0
        poly = None
        if fmt == "radial":
            x, y, r, pts = num("x"), num("y"), num("radius"), num("pts")
            if None not in (x, y, r, pts) and r > 0 and pts >= 3:
                poly = cls.radial(x + (num("shiftx", 0.0) or 0.0), y + (num("shifty", 0.0) or 0.0),
                                  r, int(pts), num("z", 0.0) or 0.0, snap)
        elif fmt == "ellipse":
            x, y, major, minor, pts = num("x"), num("y"), num("major"), num("minor"), num("pts")
            degs, rads = num("degs"), num("rads")
            if None not in (x, y, major, minor, pts) and major > 0 and minor > 0 and pts >= 4 \
                    and (degs is not None or rads is not None):
                poly = cls.ellipse(x, y, major, minor, int(pts), degs, rads, num("z", 0.0) or 0.0, snap)
        elif fmt in ("wedge", "piewedge"):
            x, y, lang, rang, rng = num("x"), num("y"), num("lang"), num("rang"), num("range")
            if None not in (x, y, lang, rang, rng):
                poly = cls.pie_wedge(x, y, lang, rang, rng, int(num("pts", 0) or 0), snap)
        elif fmt == "rangewedge":
            x, y, lang, rang = num("x"), num("y"), num("lang"), num("rang")
            rmin, rmax = num("range_min", 0.0), num("range_max")
            if None not in (x, y, lang, rang, rmax) and rmin < rmax:
                poly = cls.range_wedge(x, y, lang, rang, rmin, rmax, int(num("pts", 0) or 0), snap)
        elif fmt == "pylon":
            x1, y1, x2, y2 = num("x1"), num("y1"), num("x2"), num("y2")
            ap, pp = num("axis_pad"), num("perp_pad")
            if None not in (x1, y1, x2, y2, ap, pp) and ap >= 0 and pp >= 0:
                poly = cls.pylon(x1, y1, x2, y2, ap, pp, num("z", 0.0) or 0.0, snap)
        elif fmt == "oval":
            x, y, rad, length, ang = num("x"), num("y"), num("rad"), num("len", num("length")), num("ang")
            if None not in (x, y, rad, length, ang) and rad > 0:
                poly = cls.oval(x, y, rad, length, ang, num("draw_degs", 5.0) or 5.0, snap)
        if poly is None:
            if fmt not in ("radial", "ellipse", "wedge", "piewedge", "rangewedge", "pylon", "oval"):
                return None
            poly = cls()
        poly.format = fmt
        for k, v in common:
            if not poly.set_param(k, v):
                poly.extra[k] = v
        return poly

    _PREFIXES = (("radial::", "radial"), ("radial:", "shortradial"), ("ellipse::", "ellipse"),
                 ("ellipse:", "ellipse"), ("piewedge:", "piewedge"), ("rangewedge:", "rangewedge"),
                 ("wedge:", "wedge"), ("pylon:", "pylon"), ("oval:", "oval"))

    @classmethod
    def _short_radial(cls, body):
        parts = [p.strip() for p in body.split(",")]
        if not 4 <= len(parts) <= 6 or not all(is_number(p) for p in parts[:4]):
            return None
        x, y, r, pts = (float(p) for p in parts[:4])
        if r <= 0 or pts < 1:
            return None
        snap = max(0.0, float(parts[4])) if len(parts) >= 5 and is_number(parts[4]) else 0.0
        poly = cls.radial(x, y, r, int(pts), 0.0, snap)
        if len(parts) == 6:
            poly.label = parts[5]
        return poly

    @classmethod
    def from_spec(cls, spec):
        s = spec.strip()
        low = s.lower()
        for prefix, fmt in cls._PREFIXES:
            if low.startswith(prefix):
                body = s[len(prefix):]
                if fmt == "shortradial":
                    poly = cls._short_radial(body)
                else:
                    poly = cls._from_format(fmt, tokenize_spec(body))
                return poly if poly is not None else cls()
        tokens = tokenize_spec(s) if ("=" in s) else []
        fmt = next((v.lower() for k, v in tokens if k == "format" and v), None)
        if fmt:
            poly = cls._from_format(fmt, tokens)
            if poly is not None:
                return poly
            bad = cls()
            bad.unsupported_format = fmt
            return bad
        if "=" not in s and ":" in s:
            poly = cls()
            poly._parse_abbreviated(s)
            return poly
        poly = cls()
        poly._pending_snap = 0.0
        poly._apply_tokens(tokens)
        poly.apply_snap(poly._pending_snap)
        del poly._pending_snap
        return poly

    def __repr__(self):
        return f"XYPolygon({self.size()} pts, label={self.label!r})"
