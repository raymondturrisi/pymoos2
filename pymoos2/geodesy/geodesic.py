"""WGS84 geodesics through PROJ. Bearings are degrees clockwise from true
north in [0, 360).
"""

import math

from pyproj import Geod

WGS84 = Geod(ellps="WGS84")


def _finite(*vals):
    for v in vals:
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise ValueError(f"expected a finite number, got {v!r}")


def _check_lat(*lats):
    for lat in lats:
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"latitude {lat} is outside -90..90")


def inverse(lat1, lon1, lat2, lon2):
    """(distance m, bearing at point 1, bearing at point 2 continuing onward)."""
    _finite(lat1, lon1, lat2, lon2)
    _check_lat(lat1, lat2)
    az12, az21, dist = WGS84.inv(lon1, lat1, lon2, lat2)
    return dist, az12 % 360.0, (az21 + 180.0) % 360.0


def distance(lat1, lon1, lat2, lon2):
    """Geodesic distance in meters."""
    return inverse(lat1, lon1, lat2, lon2)[0]


def bearing(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 toward point 2."""
    return inverse(lat1, lon1, lat2, lon2)[1]


def forward(lat, lon, bearing_deg, distance_m):
    """(lat, lon) reached by going distance_m along the geodesic that leaves at bearing_deg."""
    _finite(lat, lon, bearing_deg, distance_m)
    _check_lat(lat)
    lon2, lat2, _ = WGS84.fwd(lon, lat, bearing_deg, distance_m)
    return lat2, (lon2 + 180.0) % 360.0 - 180.0


def path(lat1, lon1, lat2, lon2, n):
    """n points strictly between the ends, equally spaced along the geodesic."""
    _finite(lat1, lon1, lat2, lon2)
    _check_lat(lat1, lat2)
    if n < 1:
        return []
    return [(lat, lon) for lon, lat in WGS84.npts(lon1, lat1, lon2, lat2, int(n))]
