"""XYObject — base class for VIEW_* geometry DTOs: shared visual and
lifecycle fields.
"""

from pymoos2.core.strutil import parse_string_q, double_to_string_x, to_bool
from pymoos2.dtos.geometry.colors import is_color


def tokenize_spec(spec):
    """'k=v,k=v' to [(key_lower, value)], not splitting inside braces or double
    quotes; a token without '=' has value None.
    """
    out = []
    for tok in parse_string_q(spec.strip(), ","):
        tok = tok.strip()
        if not tok:
            continue
        if "=" in tok:
            k, v = tok.split("=", 1)
            out.append((k.strip().lower(), v.strip()))
        else:
            out.append((tok.lower(), None))
    return out


class XYObject:
    KIND = "object"

    def __init__(self, **kwargs):
        self.label = ""
        self.msg = ""
        self.source = ""
        self.vsource = ""
        self.id = ""
        self.type = ""
        self.active = True
        self.label_color = ""
        self.edge_color = ""
        self.vertex_color = ""
        self.fill_color = ""
        self.time = None
        self.duration = None
        self.vertex_size = None
        self.edge_size = None
        self.fill_transparency = None
        self.extra = {}
        self._init_fields()
        for k, v in kwargs.items():
            if not hasattr(self, k) or k.startswith("_"):
                raise TypeError(f"{type(self).__name__} has no field '{k}'")
            setattr(self, k, v)

    def _init_fields(self):
        """Hook: set subclass defaults (runs before kwargs)."""
        pass

    def stamp(self, now):
        """Set time to now if the spec had none."""
        if self.time is None or self.time <= 0:
            self.time = now

    def expired(self, now):
        """True once more than duration has passed since time (both set and positive)."""
        if self.time is None or self.duration is None:
            return False
        if self.duration < 0 or self.time <= 0:
            return False
        return (now - self.time) > self.duration

    def set_param(self, key, value):
        """Apply one common key. Returns False for keys this class does not know."""
        k = key.lower()
        if value is None:
            return False
        if k in ("label", "msg", "source", "vsource", "id", "type"):
            setattr(self, k, value)
        elif k == "active":
            if value.lower() in ("true", "false"):
                self.active = to_bool(value)
        elif k in ("label_color", "edge_color", "vertex_color", "fill_color"):
            if is_color(value):
                setattr(self, k, value)
        elif k in ("time", "duration", "dur", "vertex_size", "edge_size", "fill_transparency"):
            try:
                f = float(value)
            except ValueError:
                return True
            if k == "dur":
                k = "duration"
            if k == "duration":
                self.duration = f if f >= 0 else -1.0
            elif k == "fill_transparency":
                self.fill_transparency = min(1.0, max(0.0, f))
            elif k in ("vertex_size", "edge_size"):
                if f >= 0:
                    setattr(self, k, f)
            else:
                self.time = f
        else:
            return False
        return True

    def _common_spec(self, active=None):
        """Common fields as a spec; active= forces the active token."""
        parts = []
        if active is True:
            parts.append("active=true")
        elif active is False or not self.active:
            parts.append("active=false")
        for key in ("label", "msg", "source", "vsource", "id"):
            v = getattr(self, key)
            if v:
                parts.append(f"{key}={v}")
        for key in ("label_color", "edge_color", "vertex_color", "fill_color"):
            v = getattr(self, key)
            if v:
                parts.append(f"{key}={v}")
        if self.time is not None:
            parts.append(f"time={double_to_string_x(self.time, 2)}")
        if self.duration is not None:
            parts.append(f"duration={double_to_string_x(self.duration, 2)}")
        if self.vertex_size is not None:
            parts.append(f"vertex_size={double_to_string_x(self.vertex_size, 1)}")
        if self.edge_size is not None:
            parts.append(f"edge_size={double_to_string_x(self.edge_size, 1)}")
        if self.fill_transparency is not None:
            parts.append(f"fill_transparency={double_to_string_x(self.fill_transparency, 2)}")
        return parts

    def _join(self, own_parts, active=None):
        return ",".join(list(own_parts) + self._common_spec(active))

    def _set_own_param(self, key, value):
        """Subclass hook: return True if the key was consumed."""
        return False

    def _apply_tokens(self, tokens):
        for k, v in tokens:
            if self._set_own_param(k, v):
                continue
            if self.set_param(k, v):
                continue
            self.extra[k] = v
        return self

    @classmethod
    def from_spec(cls, spec):
        obj = cls()
        obj._apply_tokens(tokenize_spec(spec))
        return obj

    def valid(self):
        return True

    def get_spec(self, active=None):
        return self._join([], active)

    def get_spec_inactive(self):
        """The erase spec: label plus active=false."""
        return self._join(self._inactive_parts(), active=False)

    def _inactive_parts(self):
        return []

    def _fields_dict(self):
        return {}

    def to_dict(self):
        d = {
            "kind": self.KIND,
            "label": self.label,
            "active": self.active,
        }
        for key in ("msg", "source", "vsource", "id", "type"):
            v = getattr(self, key)
            if v:
                d[key] = v
        style = {}
        for key in ("label_color", "edge_color", "vertex_color", "fill_color",
                    "vertex_size", "edge_size", "fill_transparency"):
            v = getattr(self, key)
            if v not in ("", None):
                style[key] = v
        d["style"] = style
        if self.time is not None:
            d["time"] = self.time
        if self.duration is not None:
            d["duration"] = self.duration
        d.update(self._fields_dict())
        return d

    def __repr__(self):
        return f"{type(self).__name__}(label={self.label!r})"
