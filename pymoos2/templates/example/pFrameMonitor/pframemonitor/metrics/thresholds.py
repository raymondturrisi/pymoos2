"""Warning thresholds on frame distortion. Defaults are in
data/thresholds.json; a mission can name its own file and override single
values.
"""

import json
import os
from dataclasses import dataclass, fields, replace

DEFAULTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "thresholds.json")


@dataclass(frozen=True)
class Thresholds:
    scale_ppm: float
    convergence_deg: float
    range_error_m: float
    bearing_error_deg: float

    def exceeded(self, d):
        """[(metric, value, limit), ...] for every metric of Distortion d over its limit."""
        return [(f.name, getattr(d, f.name), getattr(self, f.name)) for f in fields(self)
                if abs(getattr(d, f.name)) > getattr(self, f.name)]

    def with_overrides(self, overrides):
        """A copy with any of {metric: limit} replaced; unknown names raise KeyError."""
        names = {f.name for f in fields(self)}
        bad = set(overrides) - names
        if bad:
            raise KeyError(f"unknown threshold(s): {', '.join(sorted(bad))}")
        return replace(self, **{k: float(v) for k, v in overrides.items()})


def load_thresholds(path=DEFAULTS_PATH):
    """Thresholds from a JSON file of {metric: limit}; every metric must be present and positive."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    names = [f.name for f in fields(Thresholds)]
    missing = [n for n in names if n not in raw]
    if missing:
        raise ValueError(f"{path}: missing {', '.join(missing)}")
    vals = {n: float(raw[n]) for n in names}
    if any(v <= 0 for v in vals.values()):
        raise ValueError(f"{path}: thresholds must be positive")
    return Thresholds(**vals)
