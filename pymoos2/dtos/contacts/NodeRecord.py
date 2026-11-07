"""NODE_REPORT record.

    NAME=alpha,X=23.4,Y=-12.1,SPD=2.4,HDG=45,DEP=5,LAT=43.82,LON=-70.33,TYPE=kayak,...

Parsing accepts field aliases and the braced form. Unknown keys go to
.properties; .fields_set holds the fields that were present.
"""

import math
import time as _time

from pymoos2.core.strutil import double_to_string_x, is_number, parse_string_z, strip_braces

KNOWN_VEHICLE_TYPES = (
    "auv", "kayak", "uuv", "usv", "glider", "asv", "ship", "mokai", "longship", "buoy",
    "heron", "swimmer", "cray", "bcray", "crayx", "wamv", "bcrayx", "smr", "skyw", "skywalker",
)

_NUMERIC = {
    "TIME": "timestamp", "UTC_TIME": "timestamp",
    "X": "x", "Y": "y", "LAT": "lat", "LON": "lon",
    "SPD": "speed", "SPEED": "speed",
    "HDG": "heading", "HEADING": "heading",
    "DEP": "depth", "DEPTH": "depth",
    "LENGTH": "length", "LEN": "length",
    "BEAM": "beam",
    "YAW": "yaw", "PITCH": "pitch",
    "ALT": "altitude", "ALTITUDE": "altitude",
    "HDG_OG": "heading_og", "COG": "cog", "SPD_OG": "speed_og", "SPEED_OG": "speed_og",
    "TRANSPARENCY": "transparency",
}
_STRINGS = {
    "NAME": "name", "TYPE": "type", "MODE": "mode", "MODE_AUX": "mode_aux",
    "ALLSTOP": "allstop", "COLOR": "color", "GROUP": "group", "VSOURCE": "vsource",
    "LOAD_WARNING": "load_warning",
}


def heading_to_radians(heading_deg):
    """Heading in degrees to a math angle in radians, wrapped to (-pi, pi]."""
    rad = math.radians(90.0 - heading_deg)
    while rad > math.pi:
        rad -= 2 * math.pi
    while rad <= -math.pi:
        rad += 2 * math.pi
    return rad


class NodeRecord:
    """Vehicle state from a NODE_REPORT."""

    __slots__ = (
        "name", "type", "group", "color", "vsource",
        "x", "y", "lat", "lon",
        "speed", "speed_og", "heading", "heading_og", "cog", "yaw", "pitch",
        "depth", "altitude",
        "length", "beam",
        "timestamp", "index", "transparency", "thrust_mode_reverse",
        "mode", "mode_aux", "allstop",
        "trajectory", "load_warning",
        "properties", "fields_set",
    )

    def __init__(self, **kwargs):
        self.name = ""
        self.type = ""
        self.group = ""
        self.color = ""
        self.vsource = ""
        self.x = 0.0
        self.y = 0.0
        self.lat = 0.0
        self.lon = 0.0
        self.speed = 0.0
        self.speed_og = 0.0
        self.heading = 0.0
        self.heading_og = 0.0
        self.cog = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.depth = 0.0
        self.altitude = 0.0
        self.length = 0.0
        self.beam = 0.0
        self.timestamp = 0.0
        self.index = 0
        self.transparency = 1.0
        self.thrust_mode_reverse = False
        self.mode = ""
        self.mode_aux = ""
        self.allstop = ""
        self.trajectory = ""
        self.load_warning = ""
        self.properties = {}
        self.fields_set = set()

        for k, v in kwargs.items():
            if k not in self.__slots__ or k in ("properties", "fields_set"):
                raise TypeError(f"NodeRecord has no field '{k}'")
            setattr(self, k, v)
            self.fields_set.add(k)

    def has(self, *fields):
        return all(f in self.fields_set for f in fields)

    def has_xy(self):
        return self.has("x", "y")

    def has_latlon(self):
        return self.has("lat", "lon")

    def valid(self):
        """True with a name, speed and heading, and x/y or lat/lon."""
        return bool(self.name) and self.has("speed", "heading") and (self.has_xy() or self.has_latlon())

    def set(self, field, value):
        setattr(self, field, value)
        self.fields_set.add(field)

    def set_xy(self, x, y):
        self.set("x", float(x))
        self.set("y", float(y))

    def set_latlon(self, lat, lon):
        self.set("lat", float(lat))
        self.set("lon", float(lon))

    def get_spec(self, terse=False, coord_policy_global=False):
        """Serialize as a NODE_REPORT."""
        f = double_to_string_x
        s = f"NAME={self.name}"
        if not coord_policy_global:
            if "x" in self.fields_set:
                s += ",X=" + f(self.x, 2)
            if "y" in self.fields_set:
                s += ",Y=" + f(self.y, 2)
        if "speed" in self.fields_set:
            s += ",SPD=" + f(self.speed, 2)
        if "heading" in self.fields_set:
            s += ",HDG=" + f(self.heading, 2)
        if "cog" in self.fields_set:
            s += ",COG=" + f(self.cog, 2)
        if "depth" in self.fields_set and not terse:
            s += ",DEP=" + f(self.depth, 2)
        if coord_policy_global or not terse:
            if "lat" in self.fields_set:
                s += ",LAT=" + f(self.lat, 8)
            if "lon" in self.fields_set:
                s += ",LON=" + f(self.lon, 8)
        for key, attr in (("TYPE", "type"), ("COLOR", "color"), ("GROUP", "group"),
                          ("VSOURCE", "vsource"), ("MODE", "mode"), ("MODE_AUX", "mode_aux"),
                          ("ALLSTOP", "allstop"), ("LOAD_WARNING", "load_warning")):
            v = getattr(self, attr)
            if v:
                s += f",{key}={v}"
        if "altitude" in self.fields_set:
            s += ",ALTITUDE=" + f(self.altitude, 2)
        if "speed_og" in self.fields_set:
            s += ",SPD_OG=" + f(self.speed_og, 2)
        if "heading_og" in self.fields_set:
            s += ",HDG_OG=" + f(self.heading_og, 2)
        if self.index:
            s += f",INDEX={int(self.index)}"
        if self.thrust_mode_reverse:
            s += ",THRUST_MODE_REVERSE=true"
        if "yaw" in self.fields_set and not terse:
            s += ",YAW=" + f(heading_to_radians(self.heading), 7)
        if "timestamp" in self.fields_set:
            s += ",TIME=" + f(self.timestamp, 2)
        if "transparency" in self.fields_set:
            s += ",TRANSPARENCY=" + f(self.transparency, 2)
        if "length" in self.fields_set:
            s += ",LENGTH=" + f(self.length, 2)
        if "beam" in self.fields_set:
            s += ",BEAM=" + f(self.beam, 2)
        if self.trajectory:
            s += ",TRAJECTORY={" + self.trajectory + "}"
        for k, v in self.properties.items():
            s += f",{k}={v}"
        return s

    @classmethod
    def from_spec(cls, spec):
        """Parse a NODE_REPORT (comma separated, or the braced JSON-ish form)."""
        rec = cls()
        s = spec.strip()
        if s.startswith("{") and s.endswith("}"):
            inner = s[1:-1].replace('"', "")
            items = [tok.strip() for tok in inner.split(",")]
            pairs = [tuple(p.strip() for p in tok.split(":", 1)) for tok in items if ":" in tok]
        else:
            pairs = []
            for tok in parse_string_z(s, ",", "{"):
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    pairs.append((k.strip(), v.strip()))
        for key, value in pairs:
            param = key.upper()
            if param in _STRINGS:
                rec.set(_STRINGS[param], value)
            elif param == "INDEX":
                rec.set("index", int(float(value)) if is_number(value) else 0)
            elif param in _NUMERIC and is_number(value):
                rec.set(_NUMERIC[param], float(value))
            elif param == "THRUST_MODE_REVERSE":
                rec.set("thrust_mode_reverse", value.lower() == "true")
            elif param == "TRAJECTORY":
                rec.set("trajectory", strip_braces(value))
            else:
                rec.properties[key] = value
        return rec

    def to_dict(self):
        d = {"name": self.name}
        for attr in ("type", "group", "color", "vsource", "mode", "mode_aux", "allstop",
                     "load_warning", "trajectory"):
            v = getattr(self, attr)
            if v:
                d[attr] = v
        for attr in ("x", "y", "lat", "lon", "speed", "speed_og", "heading", "heading_og",
                     "cog", "yaw", "pitch", "depth", "altitude", "length", "beam",
                     "timestamp", "transparency"):
            if attr in self.fields_set:
                d[attr] = getattr(self, attr)
        if self.index:
            d["index"] = self.index
        if self.thrust_mode_reverse:
            d["thrust_mode_reverse"] = True
        if self.properties:
            d["properties"] = dict(self.properties)
        return d

    def elapsed_time(self, now=None):
        if now is None:
            now = _time.time()
        return now - self.timestamp

    def __repr__(self):
        return f"NodeRecord({self.name} x={self.x:.1f} y={self.y:.1f} hdg={self.heading:.0f})"


def normalize_vehicle_type(vtype):
    """Map type aliases: uuv to auv, slocum and seaglider to glider, unknown to ship."""
    t = (vtype or "").lower()
    if t == "uuv":
        return "auv"
    if t in ("slocum", "seaglider"):
        return "glider"
    if t in KNOWN_VEHICLE_TYPES:
        return t
    return "ship"


def default_vehicle_length(vtype):
    """Default length in meters for a vehicle type."""
    t = (vtype or "").lower()
    if t in ("auv", "kayak", "heron"):
        return 3.0
    if t == "glider":
        return 2.0
    if "cray" in t:
        return 1.5
    if t == "ship":
        return 12.0
    if t == "longship":
        return 15.0
    if t in ("wamv", "smr"):
        return 6.0
    return 0.0
