"""Geodesy against PROJ: round trips, continuity, geodesics, distortion and
reframing.
"""

import math
import random
import threading

import pytest
from pyproj import Proj, Transformer

from pymoos2.geodesy import (LocalFrame, geodesic, distortion, distortion_xy, leg_deviation,
                             reframe_xy, reframe_many, reframe_heading, reframe_object,
                             utm_zone_number, utm_band_letter)
from pymoos2.geodesy.info import parse_info, find_image, image_search_dirs
from pymoos2.dtos.geometry import XYPolygon, XYPoint, XYVector, XYSeglr, XYCircle

MIT = (42.358456, -71.087589)
UM = 1e-6


def ground_gap(a, b):
    return geodesic.distance(a[0], a[1], b[0], b[1])


def random_points(origin, max_m, n, seed):
    rng = random.Random(seed)
    return [geodesic.forward(origin[0], origin[1], rng.uniform(0, 360), rng.uniform(0, max_m)) for _ in range(n)]


def test_origin_is_zero_and_metadata():
    f = LocalFrame(*MIT)
    x, y = f.to_xy(*MIT)
    assert abs(x) < 1e-9 and abs(y) < 1e-9
    assert (f.zone, f.south, f.utm_zone, f.projection, f.epoch) == (19, False, "19T", "utm", 0)
    a = LocalFrame(*MIT, projection="aeqd")
    assert a.zone is None and a.utm_zone is None and a.to_xy(*MIT) == pytest.approx((0, 0), abs=1e-9)
    assert LocalFrame(10.0, 190.0).lon == -170.0


@pytest.mark.parametrize("args", [
    (float("nan"), 0.0), (0.0, float("inf")), (95.0, 0.0), ("42", 0.0), (True, 0.0),
    (42.0, -71.0, "mercator"), (42.0, -71.0, "utm", -1), (42.0, -71.0, "utm", 1.5), (42.0, -71.0, "utm", True),
    (85.0, 0.0), (-81.0, 0.0),
])
def test_bad_frames_raise(args):
    with pytest.raises(ValueError):
        LocalFrame(*args)


def test_aeqd_works_at_the_poles():
    north = LocalFrame(89.999, 0.0, "aeqd")
    lat, lon = north.to_latlon(*north.to_xy(89.5, 135.0))
    assert ground_gap((lat, lon), (89.5, 135.0)) < UM
    assert LocalFrame(-90.0, 0.0, "aeqd").to_xy(-89.0, 45.0)


def test_bad_points_raise():
    f = LocalFrame(*MIT)
    for args in [(float("nan"), 0.0), (42.0, None), ("1", 2)]:
        with pytest.raises(ValueError):
            f.to_xy(*args)
        with pytest.raises(ValueError):
            f.to_latlon(*args)
    with pytest.raises(ValueError):
        f.to_xy_many([(42.0, -71.0), (float("nan"), 0.0)])
    assert f.to_xy_many([]) == [] and f.to_latlon_many([]) == []


def test_zone_rules():
    assert utm_zone_number(*MIT) == 19
    assert utm_zone_number(60.0, 5.0) == 32
    assert utm_zone_number(75.0, 10.0) == 33
    assert utm_zone_number(75.0, 25.0) == 35 and utm_zone_number(75.0, 35.0) == 37 and utm_zone_number(75.0, 5.0) == 31
    assert utm_zone_number(0.0, 180.0) == 1 and utm_zone_number(0.0, 179.999) == 60
    assert utm_band_letter(42.0) == "T" and utm_band_letter(-80.0) == "C" and utm_band_letter(84.0) == "X"
    with pytest.raises(ValueError):
        utm_band_letter(85.0)
    assert LocalFrame(-33.86, 151.21).south and LocalFrame(-33.86, 151.21).to_spec().endswith("zone=56S")


def test_spec_round_trip_and_identity():
    for f in (LocalFrame(*MIT), LocalFrame(-33.86, 151.21, "aeqd", 4)):
        g = LocalFrame.from_spec(f.to_spec())
        assert g == f and hash(g) == hash(f) and repr(f).startswith("LocalFrame(")
    assert LocalFrame(*MIT) != LocalFrame(*MIT, epoch=1) and LocalFrame(*MIT) != "frame"
    for bad in ["epoch=0,lat=1", "junk", "epoch=0,lat=42.3,lon=-71.1,proj=utm,zone=18N"]:
        with pytest.raises(ValueError):
            LocalFrame.from_spec(bad)


def test_moved_to():
    f = LocalFrame(*MIT, projection="aeqd", epoch=3)
    g = f.moved_to(43.0, -70.0)
    assert (g.epoch, g.projection, g.lat, g.lon) == (4, "aeqd", 43.0, -70.0)
    assert (f.lat, f.epoch) == (MIT[0], 3)


def test_utm_matches_proj_exactly():
    f = LocalFrame(*MIT)
    t = Transformer.from_crs(4326, 32619, always_xy=True)
    e0, n0 = t.transform(MIT[1], MIT[0])
    for lat, lon in random_points(MIT, 50_000, 200, seed=1):
        e, n = t.transform(lon, lat)
        x, y = f.to_xy(lat, lon)
        assert abs(x - (e - e0)) < 1e-8 and abs(y - (n - n0)) < 1e-8


@pytest.mark.parametrize("proj,max_m", [("utm", 1_000_000), ("aeqd", 5_000_000)])
def test_round_trip_is_sub_micrometer(proj, max_m):
    f = LocalFrame(*MIT, projection=proj)
    worst = 0.0
    for p in random_points(MIT, max_m, 500, seed=2):
        back = f.to_latlon(*f.to_xy(*p))
        worst = max(worst, ground_gap(p, back))
    assert worst < UM, worst
    for x, y in [(0.0, 0.0), (1234.5, -987.6), (-250_000.0, 400_000.0)]:
        x2, y2 = f.to_xy(*f.to_latlon(x, y))
        assert abs(x2 - x) < UM and abs(y2 - y) < UM


def test_batch_equals_scalar():
    f = LocalFrame(*MIT)
    pts = random_points(MIT, 20_000, 50, seed=3)
    xy = f.to_xy_many(pts)
    assert xy == [f.to_xy(*p) for p in pts]
    back = f.to_latlon_many(xy)
    assert all(ground_gap(a, b) < UM for a, b in zip(pts, back))
    assert f.to_xy_many(iter(pts[:3])) == xy[:3]


def test_continuous_across_utm_zone_lines():
    f = LocalFrame(*MIT)
    lat, lon = MIT
    prev = f.to_xy(lat, lon)
    for _ in range(1500):
        lat, lon = geodesic.forward(lat, lon, 90.0, 1000.0)
        cur = f.to_xy(lat, lon)
        step = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
        assert 990.0 < step < 1030.0, (lon, step)
        prev = cur
    assert lon > -55.0


@pytest.mark.parametrize("proj", ["utm", "aeqd"])
def test_continuous_across_the_antimeridian(proj):
    f = LocalFrame(-17.7, 179.95, proj)
    x1, y1 = f.to_xy(-17.7, 179.99)
    x2, y2 = f.to_xy(-17.7, -179.99)
    true_m = geodesic.distance(-17.7, 179.99, -17.7, -179.99)
    scale = 1.0 + distortion(f, -17.7, 180.0).scale_ppm / 1e6
    assert 0 < x1 < x2 and math.hypot(x2 - x1, y2 - y1) == pytest.approx(true_m * scale, abs=0.01)


def test_southern_origin_continuous_over_the_equator():
    f = LocalFrame(-0.5, 30.0)
    _, y1 = f.to_xy(-0.001, 30.0)
    _, y2 = f.to_xy(0.001, 30.0)
    assert 200.0 < y2 - y1 < 240.0


def test_threads_share_a_frame_safely():
    f = LocalFrame(*MIT)
    pts = random_points(MIT, 30_000, 200, seed=4)
    expect = [f.to_xy(*p) for p in pts]
    errors = []

    def worker():
        for _ in range(5):
            if [f.to_xy(*p) for p in pts] != expect:
                errors.append("mismatch")
    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_geodesic_known_values():
    assert geodesic.distance(0, 0, 0, 1) == pytest.approx(111319.49079327357, abs=1e-6)
    assert geodesic.distance(0, 0, 1, 0) == pytest.approx(110574.38855779878, abs=1e-6)
    assert geodesic.bearing(0, 0, 0, 1) == pytest.approx(90.0) and geodesic.bearing(0, 0, 1, 0) == pytest.approx(0.0)
    assert geodesic.bearing(0, 1, 0, 0) == pytest.approx(270.0)
    d, b1, b2 = geodesic.inverse(*MIT, 51.4779, -0.0015)
    assert 5.2e6 < d < 5.3e6 and 0 <= b1 < 360 and 0 <= b2 < 360
    assert geodesic.distance(10.0, 179.9, 10.0, -179.9) < 25_000


def test_geodesic_forward_inverse_consistency():
    for lat, lon in random_points(MIT, 9_000_000, 100, seed=5):
        d, b, _ = geodesic.inverse(*MIT, lat, lon)
        assert ground_gap(geodesic.forward(*MIT, b, d), (lat, lon)) < UM
    lat, lon = geodesic.forward(10.0, 179.99, 90.0, 5000.0)
    assert -180.0 <= lon < 180.0 and lon < 0


def test_geodesic_path_and_validation():
    pts = geodesic.path(*MIT, 51.4779, -0.0015, 9)
    total = geodesic.distance(*MIT, 51.4779, -0.0015)
    assert len(pts) == 9
    gaps = [ground_gap(a, b) for a, b in zip([MIT] + pts, pts + [(51.4779, -0.0015)])]
    assert max(gaps) - min(gaps) < 1e-3 and sum(gaps) == pytest.approx(total, abs=1e-3)
    assert geodesic.path(0, 0, 1, 1, 0) == []
    for bad in [(91.0, 0, 0, 0), (0, float("nan"), 0, 0)]:
        with pytest.raises(ValueError):
            geodesic.distance(*bad)
    with pytest.raises(ValueError):
        geodesic.forward(95.0, 0.0, 0.0, 1.0)


def test_distortion_at_the_origin():
    d = distortion(LocalFrame(*MIT, projection="aeqd"), *MIT)
    assert abs(d.scale_ppm) < 0.05 and abs(d.convergence_deg) < 1e-6
    assert d.range_m == 0.0 and d.range_error_m == 0.0 and d.bearing_error_deg == 0.0
    d = distortion(LocalFrame(*MIT), *MIT)
    assert -45 < d.scale_ppm < -35
    assert d.convergence_deg == pytest.approx(1.4, abs=0.05)


def test_scale_matches_a_numerical_measurement():
    f = LocalFrame(*MIT)
    for lat, lon in random_points(MIT, 600_000, 20, seed=6):
        d = distortion(f, lat, lon)
        for brg in (0.0, 90.0):
            lat2, lon2 = geodesic.forward(lat, lon, brg, 10.0)
            (x1, y1), (x2, y2) = f.to_xy(lat, lon), f.to_xy(lat2, lon2)
            measured_ppm = (math.hypot(x2 - x1, y2 - y1) / 10.0 - 1.0) * 1e6
            assert measured_ppm == pytest.approx(d.scale_ppm, abs=0.5)


def test_convergence_matches_proj_and_heading_rule():
    f = LocalFrame(*MIT)
    for lat, lon in random_points(MIT, 500_000, 20, seed=7):
        d = distortion(f, lat, lon)
        assert abs(d.convergence_deg) == pytest.approx(abs(Proj(f.crs).get_factors(lon, lat).meridian_convergence), abs=1e-6)
        lat2, lon2 = geodesic.forward(lat, lon, 60.0, 5.0)
        (x1, y1), (x2, y2) = f.to_xy(lat, lon), f.to_xy(lat2, lon2)
        grid = math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360.0
        assert grid == pytest.approx((60.0 + d.convergence_deg) % 360.0, abs=1e-4)


def test_range_and_bearing_error_grow_with_distance():
    f = LocalFrame(*MIT)
    near = distortion_xy(f, 1000.0, 1000.0)
    far = distortion_xy(f, 300_000.0, 300_000.0)
    assert abs(near.range_error_m) < 0.1 and abs(far.range_error_m) > 10 * abs(near.range_error_m)
    assert abs(far.bearing_error_deg) > abs(near.bearing_error_deg)
    assert far.range_m == pytest.approx(geodesic.distance(*MIT, far.lat, far.lon))
    spec = far.to_spec()
    assert spec.startswith("x=300000.000,y=300000.000,") and "scale_ppm=" in spec


def test_leg_deviation():
    f = LocalFrame(*MIT)
    assert leg_deviation(f, 0, 0, 1000, 0) < 1e-3
    assert leg_deviation(f, 0, 0, 400_000, 400_000) > 10.0
    with pytest.raises(ValueError):
        leg_deviation(f, 0, 0, 1, 1, samples=0)


def test_reframe_points_keep_their_ground_position():
    src = LocalFrame(*MIT)
    dst = src.moved_to(*geodesic.forward(*MIT, 45.0, 80_000.0))
    for x, y in [(0, 0), (50_000, 50_000), (-2000, 3000)]:
        nx, ny = reframe_xy(src, dst, x, y)
        assert ground_gap(src.to_latlon(x, y), dst.to_latlon(nx, ny)) < UM
    many = reframe_many(src, dst, [(0, 0), (10, 10)])
    assert many[0] == pytest.approx(reframe_xy(src, dst, 0, 0), abs=1e-9)
    assert reframe_xy(src, src, 123.0, 456.0) == pytest.approx((123.0, 456.0), abs=UM)


def test_reframe_heading_rotates_by_convergence_change():
    src = LocalFrame(*MIT)
    dst = LocalFrame(*MIT, projection="aeqd")
    h = reframe_heading(src, dst, 0.0, 0.0, 90.0)
    assert h == pytest.approx(90.0 - distortion(src, *MIT).convergence_deg, abs=1e-6)


def test_reframe_objects():
    src = LocalFrame(*MIT)
    dst = src.moved_to(*geodesic.forward(*MIT, 0.0, 30_000.0))
    poly = XYPolygon.from_spec("pts={0,0:100,0:100,100:0,100},label=a")
    moved = reframe_object(poly, src, dst)
    assert moved.vx != poly.vx and poly.vx == [0.0, 100.0, 100.0, 0.0]
    for (x, y), (nx, ny) in zip(zip(poly.vx, poly.vy), zip(moved.vx, moved.vy)):
        assert ground_gap(src.to_latlon(x, y), dst.to_latlon(nx, ny)) < UM
    pt = reframe_object(XYPoint.from_spec("x=10,y=20,label=p"), src, dst)
    assert ground_gap(src.to_latlon(10, 20), dst.to_latlon(pt.x, pt.y)) < UM
    vec = XYVector.from_spec("x=0,y=0,ang=45,mag=10,label=v")
    rv = reframe_object(vec, src, dst)
    assert rv.ang == pytest.approx(reframe_heading(src, dst, 0, 0, 45.0), abs=1e-9)
    circle = reframe_object(XYCircle.from_spec("x=5,y=5,radius=20,label=c"), src, dst)
    assert circle.radius == 20.0
    seglr = XYSeglr.from_spec("pts={0,0:10,10},ray=30,ray_len=5,head_size=2,label=s")
    rs = reframe_object(seglr, src, dst)
    assert rs.ray == pytest.approx(reframe_heading(src, dst, 10, 10, 30.0), abs=1e-9)


def test_info_parse_new_style(tmp_path):
    p = tmp_path / "a.info"
    p.write_text("// generated\nlat_north = 42.360264\nlat_south = 42.35415\n"
                 "lon_east  = -71.080058\nlon_west  = -71.094214\n"
                 "datum_lat = 42.358436\ndatum_lon = -71.087448\nmystery = 3\n")
    info = parse_info(str(p))
    assert info.style == "latlon" and info.valid
    assert info.bounds() == ((42.35415, -71.094214), (42.360264, -71.080058))
    assert info.datum_lat == 42.358436 and info.center == pytest.approx((42.357207, -71.087136))
    assert len(info.warnings) == 1 and "mystery" in info.warnings[0]


def test_info_parse_legacy_style(tmp_path):
    p = tmp_path / "b.info"
    p.write_text("img_centx = 0.495850\nimg_centy = 0.509000\nimg_meters = 0.048828\n")
    info = parse_info(str(p))
    assert info.style == "legacy" and info.valid and info.bounds() is None
    (s, w), (n, e) = info.bounds(2048, 2048, MIT)
    assert s < MIT[0] < n and w < MIT[1] < e
    g = LocalFrame(*MIT)
    x1, _ = g.to_xy(MIT[0], w)
    x2, _ = g.to_xy(MIT[0], e)
    assert abs((x2 - x1) - 100.0 / 0.048828) < 2.0


def test_find_image_resolution(tmp_path, monkeypatch):
    (tmp_path / "maps").mkdir()
    (tmp_path / "maps" / "foo.tif").write_bytes(b"")
    (tmp_path / "maps" / "foo.info").write_text("lat_north=1\nlat_south=0\nlon_east=1\nlon_west=0\n")
    (tmp_path / "maps" / "lonely.tif").write_bytes(b"")
    monkeypatch.setenv("IVP_IMAGE_DIRS", str(tmp_path / "maps"))
    assert find_image("foo.tif") == (str(tmp_path / "maps" / "foo.tif"), str(tmp_path / "maps" / "foo.info"))
    assert find_image("foo") is not None
    assert find_image("lonely.tif") is None
    assert find_image("maps/foo.tif", mission_dir=str(tmp_path)) is not None
    assert str(tmp_path / "maps") in image_search_dirs()
