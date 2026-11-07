"""Distortion of a local frame at a position.

  scale_ppm          worst-direction scale error: d meters in x/y is
                     d * (1 + scale_ppm / 1e6) meters on the ground
  convergence_deg    grid bearing of true north: true heading H is grid
                     bearing H + convergence_deg
  range_error_m      x/y distance from the origin minus the geodesic distance
  bearing_error_deg  x/y bearing from the origin minus the geodesic bearing
  leg_deviation()    largest gap between a straight x/y leg and the geodesic
"""

import math
from dataclasses import dataclass

from pyproj import Proj

from pymoos2.geodesy import geodesic


@dataclass(frozen=True)
class Distortion:
    lat: float
    lon: float
    x: float
    y: float
    scale_ppm: float
    convergence_deg: float
    range_m: float
    range_error_m: float
    bearing_error_deg: float

    def to_spec(self):
        return (f"x={self.x:.3f},y={self.y:.3f},scale_ppm={self.scale_ppm:.3f},"
                f"convergence_deg={self.convergence_deg:.6f},range_m={self.range_m:.3f},"
                f"range_error_m={self.range_error_m:.4f},bearing_error_deg={self.bearing_error_deg:.6f}")


def _wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def _grid_bearing_of_north(frame, lat, lon):
    x0, y0 = frame.to_xy(lat, lon)
    lat1, lon1 = geodesic.forward(lat, lon, 0.0, 1.0)
    x1, y1 = frame.to_xy(lat1, lon1)
    return math.degrees(math.atan2(x1 - x0, y1 - y0))


def distortion(frame, lat, lon):
    """Distortion of frame at (lat, lon)."""
    x, y = frame.to_xy(lat, lon)
    f = Proj(frame.crs).get_factors(lon, lat)
    a, b = f.tissot_semimajor, f.tissot_semiminor
    scale = a - 1.0 if abs(a - 1.0) >= abs(b - 1.0) else b - 1.0
    if math.hypot(x, y) < 1e-6:
        rng, rng_err, brg_err = 0.0, 0.0, 0.0
    else:
        rng, brg, _ = geodesic.inverse(frame.lat, frame.lon, lat, lon)
        grid_brg = math.degrees(math.atan2(x, y)) % 360.0
        rng_err = math.hypot(x, y) - rng
        brg_err = _wrap180(grid_brg - brg)
    return Distortion(lat, lon, x, y, scale * 1e6, _grid_bearing_of_north(frame, lat, lon), rng, rng_err, brg_err)


def distortion_xy(frame, x, y):
    """Distortion of frame at local (x, y)."""
    lat, lon = frame.to_latlon(x, y)
    return distortion(frame, lat, lon)


def leg_deviation(frame, x1, y1, x2, y2, samples=32):
    """Largest distance in meters between the straight x/y leg from (x1, y1)
    to (x2, y2) and the geodesic between the same ends.
    """
    if samples < 1:
        raise ValueError("samples must be at least 1")
    (la1, lo1), (la2, lo2) = frame.to_latlon(x1, y1), frame.to_latlon(x2, y2)
    true_pts = geodesic.path(la1, lo1, la2, lo2, samples)
    grid_pts = frame.to_latlon_many(
        [(x1 + (x2 - x1) * k / (samples + 1), y1 + (y2 - y1) * k / (samples + 1)) for k in range(1, samples + 1)])
    return max(geodesic.distance(a[0], a[1], b[0], b[1]) for a, b in zip(true_pts, grid_pts))
