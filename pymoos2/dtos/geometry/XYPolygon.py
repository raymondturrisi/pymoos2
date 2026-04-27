"""
XYPolygon — VIEW_POLYGON geometry DTO.

Inherits from XYSegList. Same spec format: pts={x1,y1:x2,y2:...}
Adds area() and contains() for convex polygons.
"""

from pymoos2.dtos.geometry.XYSegList import XYSegList


class XYPolygon(XYSegList):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def area(self):
        """Shoelace formula for polygon area."""
        n = len(self.vx)
        if n < 3:
            return 0.0
        a = 0.0
        for i in range(n):
            j = (i + 1) % n
            a += self.vx[i] * self.vy[j]
            a -= self.vx[j] * self.vy[i]
        return abs(a) / 2.0

    def contains(self, px, py):
        """Point-in-polygon test (works for convex polygons)."""
        n = len(self.vx)
        if n < 3:
            return False
        sign = None
        for i in range(n):
            j = (i + 1) % n
            dx = self.vx[j] - self.vx[i]
            dy = self.vy[j] - self.vy[i]
            cross = dx * (py - self.vy[i]) - dy * (px - self.vx[i])
            if cross != 0:
                s = cross > 0
                if sign is None:
                    sign = s
                elif s != sign:
                    return False
        return True

    def __repr__(self):
        return f"XYPolygon({self.size()} pts, label={self.label!r})"
