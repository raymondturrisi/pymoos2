"""
XYSegList — VIEW_SEGLIST geometry DTO.

Spec format: pts={x1,y1:x2,y2:...}[,<common_fields>]
"""

from pymoos2.dtos.geometry.XYObject import XYObject


class XYSegList(XYObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vx = []
        self.vy = []
        self.vz = []

    def add_vertex(self, x, y, z=0.0):
        self.vx.append(x)
        self.vy.append(y)
        self.vz.append(z)

    def size(self):
        return len(self.vx)

    def length(self):
        total = 0.0
        for i in range(1, len(self.vx)):
            dx = self.vx[i] - self.vx[i-1]
            dy = self.vy[i] - self.vy[i-1]
            total += (dx**2 + dy**2) ** 0.5
        return total

    def get_spec(self):
        pts_strs = []
        for i in range(len(self.vx)):
            if self.vz[i] != 0.0:
                pts_strs.append(f"{self.vx[i]:.2f},{self.vy[i]:.2f},{self.vz[i]:.2f}")
            else:
                pts_strs.append(f"{self.vx[i]:.2f},{self.vy[i]:.2f}")
        parts = [f"pts={{{':'.join(pts_strs)}}}"]
        parts.extend(self._common_spec())
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        params = cls._parse_params(spec)
        obj = cls()
        if "pts" in params:
            for vertex_str in params.pop("pts").split(":"):
                coords = vertex_str.strip().split(",")
                if len(coords) >= 2:
                    obj.vx.append(float(coords[0]))
                    obj.vy.append(float(coords[1]))
                    obj.vz.append(float(coords[2]) if len(coords) >= 3 else 0.0)
        cls._parse_common(obj, params)
        return obj

    def __repr__(self):
        return f"XYSegList({self.size()} pts, label={self.label!r})"
