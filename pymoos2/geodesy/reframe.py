"""Move x/y data between LocalFrames through lat/lon. Directions rotate by
the change in grid convergence.
"""

import copy

from pymoos2.geodesy.distortion import _grid_bearing_of_north

_POINT_ATTRS = (("x", "y"), ("ctrx", "ctry"), ("sx", "sy"), ("tx", "ty"), ("cpax", "cpay"))
_ANGLE_ATTRS = ("ang", "ang_low", "ang_hgh", "ray")


def reframe_xy(src, dst, x, y):
    """(x, y) of src as (x, y) of dst."""
    return dst.to_xy(*src.to_latlon(x, y))


def reframe_many(src, dst, xys):
    """[(x, y), ...] of src as dst coordinates, in one batch each way."""
    return dst.to_xy_many(src.to_latlon_many(xys))


def reframe_heading(src, dst, x, y, heading_deg):
    """A grid heading at src (x, y) as the grid heading of the same true direction in dst."""
    lat, lon = src.to_latlon(x, y)
    return (heading_deg - _grid_bearing_of_north(src, lat, lon) + _grid_bearing_of_north(dst, lat, lon)) % 360.0


def reframe_object(obj, src, dst):
    """A copy of a geometry object with positions and directions moved from src
    to dst; sizes are unchanged.
    """
    out = copy.deepcopy(obj)
    anchor = None
    for ax, ay in _POINT_ATTRS:
        px, py = getattr(obj, ax, None), getattr(obj, ay, None)
        if isinstance(px, (int, float)) and isinstance(py, (int, float)):
            if anchor is None:
                anchor = (px, py)
            nx, ny = reframe_xy(src, dst, px, py)
            setattr(out, ax, nx)
            setattr(out, ay, ny)
    if getattr(obj, "vx", None):
        pts = reframe_many(src, dst, list(zip(obj.vx, obj.vy)))
        out.vx = [p[0] for p in pts]
        out.vy = [p[1] for p in pts]
        if anchor is None:
            anchor = (obj.vx[-1], obj.vy[-1])
    if anchor is not None:
        for attr in _ANGLE_ATTRS:
            ang = getattr(obj, attr, None)
            if isinstance(ang, (int, float)) and not isinstance(ang, bool):
                setattr(out, attr, reframe_heading(src, dst, anchor[0], anchor[1], ang))
    return out
