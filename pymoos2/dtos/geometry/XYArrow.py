"""XYArrow — VIEW_ARROW geometry DTO.

Spec: ctrx=<v>,ctry=<v>,ang=<deg>[,bwid=<m>][,blen=<m>][,hwid=<m>][,hlen=<m>][,<common>]
(ctrx, ctry) is the center of the base; the head extends along ang.
Defaults: bwid 5, blen 20, hwid 10, hlen 10.
"""

from pymoos2.core.strutil import double_to_string_x, is_number
from pymoos2.dtos.geometry.XYObject import XYObject
from pymoos2.dtos.geometry.planar import project_point


class XYArrow(XYObject):
    KIND = "arrow"

    def _init_fields(self):
        self.ctrx = 0.0
        self.ctry = 0.0
        self.ang = 0.0
        self.bwid = 5.0
        self.blen = 20.0
        self.hwid = 10.0
        self.hlen = 10.0
        self._set = set()

    def valid(self):
        return {"ctrx", "ctry"} <= self._set

    def base_vertices(self):
        back = project_point(self.ang + 180, self.blen / 2.0, self.ctrx, self.ctry)
        front = project_point(self.ang, self.blen / 2.0, self.ctrx, self.ctry)
        return [project_point(self.ang - 90, self.bwid / 2.0, *back),
                project_point(self.ang + 90, self.bwid / 2.0, *back),
                project_point(self.ang + 90, self.bwid / 2.0, *front),
                project_point(self.ang - 90, self.bwid / 2.0, *front)]

    def head_vertices(self):
        front = project_point(self.ang, self.blen / 2.0, self.ctrx, self.ctry)
        tip = project_point(self.ang, self.hlen, *front)
        return [project_point(self.ang - 90, self.hwid / 2.0, *front), tip,
                project_point(self.ang + 90, self.hwid / 2.0, *front)]

    def outline(self):
        """Single 7-vertex polygon outline of base plus head."""
        b = self.base_vertices()
        h = self.head_vertices()
        return [b[0], b[1], b[2], h[2], h[1], h[0], b[3]]

    def _set_own_param(self, key, value):
        if value is None or not is_number(value):
            return False
        if key in ("ctrx", "ctry", "ang", "bwid", "blen", "hwid", "hlen"):
            setattr(self, key, float(value))
            if key in ("ctrx", "ctry"):
                self._set.add(key)
            return True
        return False

    def get_spec(self, *, active=None):
        parts = [f"ctrx={double_to_string_x(self.ctrx, 2)}", f"ctry={double_to_string_x(self.ctry, 2)}",
                 f"ang={double_to_string_x(self.ang, 2)}", f"bwid={double_to_string_x(self.bwid, 2)}",
                 f"blen={double_to_string_x(self.blen, 2)}", f"hwid={double_to_string_x(self.hwid, 2)}",
                 f"hlen={double_to_string_x(self.hlen, 2)}"]
        return self._join(parts, active)

    def _inactive_parts(self):
        return ["ctrx=0", "ctry=0"]

    def _fields_dict(self):
        return {"ctrx": self.ctrx, "ctry": self.ctry, "ang": self.ang, "bwid": self.bwid,
                "blen": self.blen, "hwid": self.hwid, "hlen": self.hlen}
