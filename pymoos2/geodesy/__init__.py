"""
Geodesy for pymoos2, on PROJ (pyproj).

  LocalFrame         a mission's x/y frame: origin, projection (utm | aeqd), epoch
  geodesic           exact WGS84 distance, bearing, forward point and paths
  distortion         how far a frame departs from the ground at a position
  reframe            carry points and geometry objects between frames

Lat/lon are degrees, x is meters east and y meters north of the origin,
bearings are degrees clockwise from north.
"""

from pymoos2.geodesy.frame import LocalFrame, PROJECTIONS, utm_zone_number, utm_band_letter
from pymoos2.geodesy import geodesic
from pymoos2.geodesy.distortion import Distortion, distortion, distortion_xy, leg_deviation
from pymoos2.geodesy.reframe import reframe_xy, reframe_many, reframe_heading, reframe_object

__all__ = [
    "LocalFrame", "PROJECTIONS", "utm_zone_number", "utm_band_letter",
    "geodesic",
    "Distortion", "distortion", "distortion_xy", "leg_deviation",
    "reframe_xy", "reframe_many", "reframe_heading", "reframe_object",
]
