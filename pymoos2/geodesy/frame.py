"""LocalFrame: a mission's local frame, converted with PROJ.

  utm   UTM in the origin's zone, x/y from the origin; continuous across
        zone lines. Origins between 80 S and 84 N.
  aeqd  azimuthal equidistant at the origin; any latitude, with exact
        distances and bearings from the origin.

Frames are immutable; moved_to() makes the next frame of a mission.
"""

import math
import threading

from pyproj import CRS, Transformer

PROJECTIONS = ("utm", "aeqd")
UTM_MIN_LAT = -80.0
UTM_MAX_LAT = 84.0


def utm_zone_number(lat, lon):
    """UTM zone for a point, with the Norway (32V) and Svalbard (31X-37X) exceptions."""
    lon = (lon + 180.0) % 360.0 - 180.0
    zone = int((lon + 180.0) // 6.0) + 1
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        return 32
    if 72.0 <= lat < 84.0 and 0.0 <= lon < 42.0:
        for lo, hi, z in ((0.0, 9.0, 31), (9.0, 21.0, 33), (21.0, 33.0, 35), (33.0, 42.0, 37)):
            if lo <= lon < hi:
                return z
    return min(zone, 60)


def utm_band_letter(lat):
    """MGRS latitude band letter (C..X); X covers 72 N to 84 N."""
    if not UTM_MIN_LAT <= lat <= UTM_MAX_LAT:
        raise ValueError(f"latitude {lat} is outside the UTM bands ({UTM_MIN_LAT} to {UTM_MAX_LAT})")
    return "CDEFGHJKLMNPQRSTUVWX"[min(int((lat + 80.0) // 8.0), 19)]


def _finite(*vals):
    for v in vals:
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise ValueError(f"expected a finite number, got {v!r}")


class LocalFrame:
    __slots__ = ("lat", "lon", "projection", "epoch", "zone", "south", "crs", "_e0", "_n0", "_local")

    def __init__(self, lat, lon, projection="utm", epoch=0):
        _finite(lat, lon)
        lat, lon = float(lat), float(lon)
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"origin latitude {lat} is outside -90..90")
        lon = (lon + 180.0) % 360.0 - 180.0
        if projection not in PROJECTIONS:
            raise ValueError(f"projection must be one of {PROJECTIONS}, got {projection!r}")
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ValueError(f"epoch must be a non-negative integer, got {epoch!r}")
        self.lat, self.lon, self.projection, self.epoch = lat, lon, projection, epoch
        if projection == "utm":
            if not UTM_MIN_LAT <= lat <= UTM_MAX_LAT:
                raise ValueError(f"origin latitude {lat} is outside the UTM range "
                                 f"({UTM_MIN_LAT} to {UTM_MAX_LAT}); use projection='aeqd'")
            self.zone = utm_zone_number(lat, lon)
            self.south = lat < 0.0
            self.crs = CRS.from_epsg((32700 if self.south else 32600) + self.zone)
        else:
            self.zone = None
            self.south = lat < 0.0
            self.crs = CRS.from_proj4(f"+proj=aeqd +lat_0={lat!r} +lon_0={lon!r} +datum=WGS84 +units=m +no_defs")
        self._local = threading.local()
        self._e0, self._n0 = 0.0, 0.0
        self._e0, self._n0 = self._fwd().transform(lon, lat)

    def _fwd(self):
        t = getattr(self._local, "fwd", None)
        if t is None:
            t = self._local.fwd = Transformer.from_crs(4326, self.crs, always_xy=True)
        return t

    def _inv(self):
        t = getattr(self._local, "inv", None)
        if t is None:
            t = self._local.inv = Transformer.from_crs(self.crs, 4326, always_xy=True)
        return t

    def to_xy(self, lat, lon):
        """(x east, y north) meters from the origin for a lat/lon in degrees."""
        _finite(lat, lon)
        e, n = self._fwd().transform(lon, lat)
        if not (math.isfinite(e) and math.isfinite(n)):
            raise ValueError(f"({lat}, {lon}) cannot be projected in {self}")
        return e - self._e0, n - self._n0

    def to_latlon(self, x, y):
        """(lat, lon) in degrees for a local x/y in meters."""
        _finite(x, y)
        lon, lat = self._inv().transform(x + self._e0, y + self._n0)
        if not (math.isfinite(lat) and math.isfinite(lon)):
            raise ValueError(f"({x}, {y}) has no lat/lon in {self}")
        return lat, lon

    def to_xy_many(self, latlons):
        """[(x, y), ...] for an iterable of (lat, lon); one PROJ call for the batch."""
        pts = [(float(a), float(b)) for a, b in latlons]
        if not pts:
            return []
        _finite(*(v for p in pts for v in p))
        es, ns = self._fwd().transform([p[1] for p in pts], [p[0] for p in pts])
        out = [(e - self._e0, n - self._n0) for e, n in zip(es, ns)]
        if not all(math.isfinite(v) for p in out for v in p):
            raise ValueError(f"a point in the batch cannot be projected in {self}")
        return out

    def to_latlon_many(self, xys):
        """[(lat, lon), ...] for an iterable of (x, y); one PROJ call for the batch."""
        pts = [(float(a), float(b)) for a, b in xys]
        if not pts:
            return []
        _finite(*(v for p in pts for v in p))
        lons, lats = self._inv().transform([p[0] + self._e0 for p in pts], [p[1] + self._n0 for p in pts])
        out = list(zip(lats, lons))
        if not all(math.isfinite(v) for p in out for v in p):
            raise ValueError(f"a point in the batch has no lat/lon in {self}")
        return out

    def moved_to(self, lat, lon):
        """The next frame of the mission: same projection, new origin, epoch + 1."""
        return LocalFrame(lat, lon, self.projection, self.epoch + 1)

    @property
    def utm_zone(self):
        """Zone and band, e.g. '19T'; None for an aeqd frame."""
        return f"{self.zone}{utm_band_letter(self.lat)}" if self.zone is not None else None

    def to_spec(self):
        """One-line spec for publishing the frame, e.g. as a MOOS variable."""
        s = f"epoch={self.epoch},lat={self.lat!r},lon={self.lon!r},proj={self.projection}"
        if self.zone is not None:
            s += f",zone={self.zone}{'S' if self.south else 'N'}"
        return s

    @classmethod
    def from_spec(cls, spec):
        """Inverse of to_spec(). The zone, if present, must match the origin."""
        kv = {}
        for tok in spec.split(","):
            if "=" not in tok:
                raise ValueError(f"malformed frame spec {spec!r}")
            k, v = tok.split("=", 1)
            kv[k.strip().lower()] = v.strip()
        missing = {"epoch", "lat", "lon", "proj"} - set(kv)
        if missing:
            raise ValueError(f"frame spec {spec!r} lacks {', '.join(sorted(missing))}")
        frame = cls(float(kv["lat"]), float(kv["lon"]), kv["proj"], int(kv["epoch"]))
        if "zone" in kv and kv["zone"] != frame.to_spec().rsplit("zone=", 1)[-1]:
            raise ValueError(f"frame spec zone {kv['zone']} does not match its origin")
        return frame

    def __eq__(self, other):
        return (isinstance(other, LocalFrame) and (self.lat, self.lon, self.projection, self.epoch)
                == (other.lat, other.lon, other.projection, other.epoch))

    def __hash__(self):
        return hash((self.lat, self.lon, self.projection, self.epoch))

    def __repr__(self):
        return f"LocalFrame({self.to_spec()})"
