"""
XYSeglr — VIEW_SEGLR geometry DTO: a seglist whose last vertex continues as
a ray. Spec: pts={...},ray=<deg>[,<common>],ray_len=<m>,head_size=<m>[,cpa=,cpax=,cpay=]
"""

from pymoos2.core.strutil import double_to_string, double_to_string_x, is_number
from pymoos2.dtos.geometry.XYSegList import XYSegList
from pymoos2.dtos.geometry.planar import project_point


class XYSeglr(XYSegList):
    KIND = "seglr"

    def _init_fields(self):
        super()._init_fields()
        self.ray = 0.0
        self.ray_len = 5.0
        self.head_size = 3.0
        self.cpa = None
        self.cpax = None
        self.cpay = None

    def ray_end(self):
        if not self.vx:
            return None
        return project_point(self.ray, self.ray_len, self.vx[-1], self.vy[-1])

    def _set_own_param(self, key, value):
        if super()._set_own_param(key, value):
            return True
        if value is None or not is_number(value):
            return False
        if key == "ray":
            self.ray = float(value)
        elif key == "ray_len":
            self.ray_len = float(value)
        elif key == "head_size":
            self.head_size = float(value)
        elif key in ("cpa", "cpax", "cpay"):
            setattr(self, key, float(value))
        else:
            return False
        return True

    def get_spec(self, precision=1, active=None):
        pts = ":".join(double_to_string(x, precision) + "," + double_to_string(y, precision)
                       for x, y in zip(self.vx, self.vy))
        parts = ["pts={" + pts + "}", "ray=" + double_to_string(self.ray, precision)]
        parts += self._common_spec(active)
        parts.append("ray_len=" + double_to_string_x(self.ray_len, 2))
        parts.append("head_size=" + double_to_string_x(self.head_size, 1))
        if self.cpa is not None and self.cpa >= 0:
            parts.append("cpa=" + double_to_string_x(self.cpa, 2))
        if self.cpax is not None and self.cpay is not None:
            parts.append("cpax=" + double_to_string_x(self.cpax, 2))
            parts.append("cpay=" + double_to_string_x(self.cpay, 2))
        return ",".join(parts)

    def _fields_dict(self):
        d = super()._fields_dict()
        d.update({"ray": self.ray, "ray_len": self.ray_len, "head_size": self.head_size})
        end = self.ray_end()
        if end:
            d["ray_end"] = list(end)
        return d
