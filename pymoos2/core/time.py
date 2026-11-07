"""
MOOS time functions with time warp support.
"""

import time as _time

from pymoos2.core.constants import MAX_TIME_WARP

_time_warp = 1.0
_skew = 0.0


def set_moos_time_warp(warp):
    """Set the process-wide time warp; raises ValueError outside
    (0, MAX_TIME_WARP].
    """
    global _time_warp
    warp = float(warp)
    if not 0 < warp <= MAX_TIME_WARP:
        raise ValueError(f"MOOSTimeWarp must be in (0, {MAX_TIME_WARP:g}], got {warp:g}")
    _time_warp = warp


def get_moos_time_warp():
    """Get the current MOOS time warp factor."""
    return _time_warp


def set_moos_skew(skew):
    """Set the clock skew (offset from MOOSDB time)."""
    global _skew
    _skew = skew


def get_moos_skew():
    """Get the current clock skew."""
    return _skew


def moos_local_time(apply_time_warping=True):
    """Local time, multiplied by the time warp when apply_time_warping is set."""
    t = _time.time()
    if apply_time_warping:
        return t * _time_warp
    return t


def moos_time(apply_time_warping=True):
    """Warped local time plus the skew to MOOSDB time."""
    return moos_local_time(apply_time_warping) + _skew


def moos_pause(milliseconds, apply_time_warping=True):
    """Sleep for milliseconds of MOOS time (milliseconds / warp of real time)."""
    sleep_ms = milliseconds
    if apply_time_warping and _time_warp > 0:
        sleep_ms /= _time_warp
    if sleep_ms > 0:
        _time.sleep(sleep_ms / 1000.0)
