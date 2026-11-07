"""Tests for the pFrameMonitor package."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymoos2.geodesy import LocalFrame, distortion          # noqa: E402
from pframemonitor.frames import frame_from_mission          # noqa: E402
from pframemonitor.metrics import load_thresholds, DEFAULTS_PATH   # noqa: E402
from pframemonitor.__main__ import parse_args                # noqa: E402


def test_packaged_defaults_load():
    assert os.path.isfile(DEFAULTS_PATH)
    t = load_thresholds()
    assert t.scale_ppm == 500.0 and t.convergence_deg == 2.0


def test_overrides_and_bad_files(tmp_path):
    t = load_thresholds().with_overrides({"scale_ppm": "200"})
    assert t.scale_ppm == 200.0
    with pytest.raises(KeyError):
        load_thresholds().with_overrides({"nope": 1})
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"scale_ppm": 1}))
    with pytest.raises(ValueError):
        load_thresholds(str(p))


def test_frame_from_mission():
    f, why = frame_from_mission(42.358456, -71.087589)
    assert isinstance(f, LocalFrame) and why == ""
    assert frame_from_mission(None, -71.0)[0] is None
    assert "outside the UTM range" in frame_from_mission(89.0, 0.0)[1]
    assert frame_from_mission(89.0, 0.0, "aeqd")[0] is not None


def test_thresholds_flag_far_positions():
    f, _ = frame_from_mission(42.358456, -71.087589)
    limits = load_thresholds()
    near = distortion(f, *f.to_latlon(500.0, 500.0))
    far = distortion(f, *f.to_latlon(800000.0, 0.0))
    assert limits.exceeded(near) == []
    assert {m for m, _, _ in limits.exceeded(far)} >= {"scale_ppm", "convergence_deg"}


def test_cli_args():
    assert parse_args(["m.moos"]) == ("m.moos", "pFrameMonitor", None)
    assert parse_args(["m.moos", "pFM2"]) == ("m.moos", "pFM2", None)
    assert parse_args(["m.moos", "--alias=pX"])[1] == "pX"
    assert parse_args(["-e"])[2] == "example"
