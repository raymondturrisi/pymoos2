"""
XYObject — base class for all MOOS geometry DTOs.

Provides common visual properties shared by all VIEW_* types:
label, source, msg, active, colors, sizes, transparency, time, duration.
"""


class XYObject:
    """Base class for MOOS geometry objects with common visual properties."""

    def __init__(self, **kwargs):
        self.label = ""
        self.source = ""
        self.msg = ""
        self.active = True
        self.label_color = ""
        self.edge_color = ""
        self.vertex_color = ""
        self.fill_color = ""
        self.time = -1.0
        self.duration = -1.0
        self.vertex_size = -1.0
        self.edge_size = -1.0
        self.fill_transparency = -1.0

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def _common_spec(self):
        """Return common property spec fields as a list of 'key=value' strings."""
        parts = []
        if not self.active:
            parts.append("active=false")
        if self.label:
            parts.append(f"label={self.label}")
        if self.msg:
            parts.append(f"msg={self.msg}")
        if self.source:
            parts.append(f"source={self.source}")
        if self.label_color:
            parts.append(f"label_color={self.label_color}")
        if self.edge_color:
            parts.append(f"edge_color={self.edge_color}")
        if self.vertex_color:
            parts.append(f"vertex_color={self.vertex_color}")
        if self.fill_color:
            parts.append(f"fill_color={self.fill_color}")
        if self.time >= 0:
            parts.append(f"time={self.time:.2f}")
        if self.duration >= 0:
            parts.append(f"duration={self.duration:.2f}")
        if self.vertex_size >= 0:
            parts.append(f"vertex_size={self.vertex_size}")
        if self.edge_size >= 0:
            parts.append(f"edge_size={self.edge_size}")
        if self.fill_transparency >= 0:
            parts.append(f"fill_transparency={self.fill_transparency}")
        return parts

    @classmethod
    def _parse_common(cls, obj, params):
        """Apply common key=value params to an XYObject instance. Returns unconsumed keys."""
        common_keys = {
            "label", "source", "msg", "label_color", "edge_color",
            "vertex_color", "fill_color", "active", "time", "duration",
            "vertex_size", "edge_size", "fill_transparency",
        }
        for k in common_keys:
            if k in params:
                v = params[k]
                if k == "active":
                    obj.active = v.lower() != "false"
                elif k in ("time", "duration", "vertex_size", "edge_size", "fill_transparency"):
                    setattr(obj, k, float(v))
                else:
                    setattr(obj, k, v)
        return {k: v for k, v in params.items() if k not in common_keys}

    @staticmethod
    def _parse_params(spec):
        """Parse a 'key=val,key=val' spec string into a dict. Handles pts={...} specially."""
        params = {}
        pts_start = spec.find("pts={")
        if pts_start >= 0:
            pts_end = spec.find("}", pts_start)
            if pts_end >= 0:
                params["pts"] = spec[pts_start + 5:pts_end]
                spec = spec[:pts_start] + spec[pts_end + 1:]

        for token in spec.split(","):
            token = token.strip()
            if not token or "=" not in token:
                continue
            k, v = token.split("=", 1)
            params[k.strip().lower()] = v.strip()
        return params
