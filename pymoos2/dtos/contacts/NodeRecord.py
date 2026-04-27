"""
NodeRecord DTO — vehicle state record, serialized in MOOS NODE_REPORT format.

Spec format:
    NAME=alpha,X=23.4,Y=-12.1,SPD=2.4,HDG=45.0,DEP=5.0,TYPE=UUV,...
"""

import time as _time


class NodeRecord:
    """Vehicle state record matching the C++ NodeRecord DTO."""

    __slots__ = (
        "name", "type", "group", "color",
        "x", "y", "lat", "lon",
        "speed", "speed_og", "heading", "cog", "yaw",
        "depth", "altitude", "pitch",
        "length", "beam",
        "timestamp",
        "mode", "mode_aux", "allstop",
        "trajectory", "load_warning",
        "properties",
    )

    def __init__(self, **kwargs):
        self.name = ""
        self.type = ""
        self.group = ""
        self.color = ""
        self.x = 0.0
        self.y = 0.0
        self.lat = 0.0
        self.lon = 0.0
        self.speed = 0.0
        self.speed_og = 0.0
        self.heading = 0.0
        self.cog = 0.0
        self.yaw = 0.0
        self.depth = 0.0
        self.altitude = 0.0
        self.pitch = 0.0
        self.length = 0.0
        self.beam = 0.0
        self.timestamp = 0.0
        self.mode = ""
        self.mode_aux = ""
        self.allstop = ""
        self.trajectory = ""
        self.load_warning = ""
        self.properties = {}

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def get_spec(self, terse=False):
        """Serialize to MOOS NODE_REPORT spec string."""
        parts = []
        parts.append(f"NAME={self.name}")
        parts.append(f"X={self.x:.2f}")
        parts.append(f"Y={self.y:.2f}")
        if self.lat != 0.0 or self.lon != 0.0:
            parts.append(f"LAT={self.lat:.6f}")
            parts.append(f"LON={self.lon:.6f}")
        parts.append(f"SPD={self.speed:.2f}")
        parts.append(f"HDG={self.heading:.1f}")
        if self.depth != 0.0:
            parts.append(f"DEP={self.depth:.2f}")
        if self.altitude != 0.0 and not terse:
            parts.append(f"ALT={self.altitude:.2f}")
        if self.cog != 0.0:
            parts.append(f"COG={self.cog:.1f}")
        if self.type:
            parts.append(f"TYPE={self.type}")
        if self.group:
            parts.append(f"GROUP={self.group}")
        if self.color:
            parts.append(f"COLOR={self.color}")
        if self.mode:
            parts.append(f"MODE={self.mode}")
        if self.mode_aux:
            parts.append(f"MODE_AUX={self.mode_aux}")
        if self.allstop:
            parts.append(f"ALLSTOP={self.allstop}")
        if self.length != 0.0:
            parts.append(f"LENGTH={self.length:.1f}")
        if self.load_warning:
            parts.append(f"LOAD_WARNING={self.load_warning}")
        parts.append(f"TIME={self.timestamp:.2f}")
        if self.trajectory:
            parts.append(f"TRAJECTORY={{{self.trajectory}}}")
        for k, v in self.properties.items():
            parts.append(f"{k}={v}")
        return ",".join(parts)

    @classmethod
    def from_spec(cls, spec):
        """Parse a NODE_REPORT spec string into a NodeRecord."""
        rec = cls()
        clean = spec
        traj_start = clean.find("TRAJECTORY={")
        if traj_start >= 0:
            traj_end = clean.find("}", traj_start)
            if traj_end >= 0:
                rec.trajectory = clean[traj_start + 12:traj_end]
                clean = clean[:traj_start] + clean[traj_end + 1:]

        for token in clean.split(","):
            token = token.strip()
            if "=" not in token:
                continue
            k, v = token.split("=", 1)
            k = k.strip().upper()
            v = v.strip()
            if k == "NAME": rec.name = v
            elif k == "X": rec.x = float(v)
            elif k == "Y": rec.y = float(v)
            elif k == "LAT": rec.lat = float(v)
            elif k == "LON": rec.lon = float(v)
            elif k == "SPD": rec.speed = float(v)
            elif k == "HDG": rec.heading = float(v)
            elif k == "DEP": rec.depth = float(v)
            elif k == "ALT": rec.altitude = float(v)
            elif k == "COG": rec.cog = float(v)
            elif k == "YAW": rec.yaw = float(v)
            elif k == "TYPE": rec.type = v
            elif k == "GROUP": rec.group = v
            elif k == "COLOR": rec.color = v
            elif k == "MODE": rec.mode = v
            elif k == "MODE_AUX": rec.mode_aux = v
            elif k == "ALLSTOP": rec.allstop = v
            elif k == "LENGTH": rec.length = float(v)
            elif k == "BEAM": rec.beam = float(v)
            elif k == "TIME": rec.timestamp = float(v)
            elif k == "LOAD_WARNING": rec.load_warning = v
            elif k == "SPEED_OG": rec.speed_og = float(v)
            elif k == "PITCH": rec.pitch = float(v)
            else:
                rec.properties[k] = v
        return rec

    def elapsed_time(self, now=None):
        if now is None:
            now = _time.time()
        return now - self.timestamp

    def __repr__(self):
        return f"NodeRecord({self.name} x={self.x:.1f} y={self.y:.1f} hdg={self.heading:.0f})"
