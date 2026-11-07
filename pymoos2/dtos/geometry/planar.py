"""
Compass-convention helpers for x/y geometry: angles are degrees clockwise
from +y (north), as MOOS-IvP geometry specs use them.
"""

import math


def rel_ang(x1, y1, x2, y2):
    """Bearing in [0, 360) from (x1, y1) to (x2, y2); 0 when the points coincide."""
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return 0.0
    return math.degrees(math.atan2(dx, dy)) % 360.0


def project_point(deg, dist, cx, cy):
    """The point dist meters from (cx, cy) along bearing deg."""
    rad = math.radians(deg)
    return cx + math.sin(rad) * dist, cy + math.cos(rad) * dist
