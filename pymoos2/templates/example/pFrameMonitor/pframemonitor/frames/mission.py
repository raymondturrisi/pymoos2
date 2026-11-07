"""The mission's LocalFrame from LatOrigin/LongOrigin."""

from pymoos2.geodesy import LocalFrame


def frame_from_mission(lat_origin, lon_origin, projection="utm"):
    """(frame, "") or (None, reason) when the origin is missing or unusable."""
    if lat_origin is None or lon_origin is None:
        return None, "LatOrigin/LongOrigin missing from the mission file"
    try:
        return LocalFrame(float(lat_origin), float(lon_origin), projection), ""
    except (TypeError, ValueError) as e:
        return None, f"bad mission origin: {e}"
