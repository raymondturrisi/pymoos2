import math

import pytest

from pymoos2.dtos.geometry import (
    XYPoint, XYSegList, XYSeglr, XYPolygon, XYCircle, XYMarker, XYVector, XYRangePulse,
    XYCommsPulse, XYArrow, XYWedge, XYOval, XYTextBox, parse_view, colors,
)
from pymoos2.dtos.contacts.NodeRecord import NodeRecord, normalize_vehicle_type, default_vehicle_length


def test_kwargs_reach_subclass_fields():
    p = XYRangePulse(x=1, y=2, radius=30, fill=0.6, label="a")
    assert p.fill == 0.6 and p.radius == 30 and p.label == "a"
    with pytest.raises(TypeError):
        XYPoint(1, 2, nonsense=3)


def test_point_spec_roundtrip_and_shorthands():
    p = XYPoint(10.5, -3, label="wpt", vertex_color="red", vertex_size=4)
    assert p.get_spec() == "x=10.5,y=-3,label=wpt,vertex_color=red,vertex_size=4"
    q = XYPoint.from_spec("x=10.5,y=-3,z=2,trans=0.3,label=wpt,vertex_color=red,vertex_size=4,dur=5")
    assert q.valid() and q.z == 2 and q.trans == 0.3 and q.duration == 5
    assert XYPoint.from_spec("3,4").valid()
    assert XYPoint.from_spec("3:4").y == 4
    a = XYPoint.from_spec("4,5:label,foo:source,bravo")
    assert a.x == 4 and a.label == "foo" and a.source == "bravo"
    assert not XYPoint.from_spec("label=foo,active=false").valid()
    assert XYPoint.from_spec("x=0,y=0,active=false,label=L").active is False
    assert XYPoint(label="L").get_spec_inactive() == "x=0,y=0,active=false,label=L"


def test_common_fields_order_matches_cpp():
    s = XYSegList()
    s.add_vertex(0, 0); s.add_vertex(10, 0)
    s.label = "r"; s.msg = "m"; s.source = "src"; s.vsource = "vs"; s.id = "7"
    s.label_color = "white"; s.edge_color = "yellow"; s.vertex_color = "blue"; s.fill_color = "red"
    s.time = 1700000000.123; s.duration = 3; s.vertex_size = 2; s.edge_size = 1.5; s.fill_transparency = 0.2
    assert s.get_spec() == ("pts={0,0:10,0},label=r,msg=m,source=src,vsource=vs,id=7,"
                            "label_color=white,edge_color=yellow,vertex_color=blue,fill_color=red,"
                            "time=1700000000.12,duration=3,vertex_size=2,edge_size=1.5,fill_transparency=0.2")


def test_seglist_props_tags_and_element_form():
    s = XYSegList.from_spec("pts={0,0,0,start:10,0:20,5,2.5},tags={0:1:a#1:2:b},label=route,edge_size=1")
    assert s.size() == 3 and s.vprop == ["start", "", ""] and s.vz[2] == 2.5
    assert s.edge_tags == [(0, 1, "a"), (1, 2, "b")]
    assert s.get_spec() == "pts={0,0,0,start:10,0:20,5,2.5},tags={0:1:a#1:2:b},label=route,edge_size=1"
    e = XYSegList.from_spec("pts={x=1,y=2:x=3,y=4},label=e")
    assert e.vertices() == [(1, 2), (3, 4)]
    ab = XYSegList.from_spec("pts:5,6:7,8:label,foo")
    assert ab.vertices() == [(5, 6), (7, 8)] and ab.label == "foo"
    assert not XYSegList.from_spec("label=x").valid()
    assert XYSegList.from_spec("label=x,active=false").valid()
    unsupported = XYSegList.from_spec("format=lawnmower,x=0,y=0,width=100,height=50,lane_width=10")
    assert not unsupported.valid() and unsupported.unsupported_format == "lawnmower"
    assert "pts" in s.to_dict() and s.to_dict()["tags"] == [[0, 1, "a"], [1, 2, "b"]]


def test_polygon_standard_and_abbreviated():
    p = XYPolygon.from_spec("pts={60,-40:60,-160:150,-160:180,-100:150,-40},label=west,edge_color=yellow")
    assert p.size() == 5 and p.is_convex() and p.label == "west"
    assert p.contains(100, -100) and not p.contains(0, 0)
    assert p.area() > 0
    a = XYPolygon.from_spec("2,3:-8,5:0,9:label,foobar:source,alpha:vertex_size,4")
    assert a.size() == 3 and a.label == "foobar" and a.vertex_size == 4
    nonconvex = XYPolygon.from_spec("pts={0,0:10,0:10,10:5,2:0,10}")
    assert nonconvex.size() == 5 and not nonconvex.is_convex() and nonconvex.valid()
    assert nonconvex.contains(1, 1) and not nonconvex.contains(5, 5)


def test_polygon_formats():
    r = XYPolygon.from_spec("format=radial,x=10,y=20,radius=5,pts=8,label=rad")
    assert r.size() == 8 and r.format == "radial" and r.label == "rad"
    e = XYPolygon.from_spec("radial:: x=17.5,y=-57.0,source=abe:station_keep,pts=32,edge_size=1,"
                            "vertex_size=0,edge_color=gray50,label=abe:station-keep-hiber,radius=-1.0,active=false")
    assert e.size() == 0 and e.active is False and e.label == "abe:station-keep-hiber"
    assert all(abs(math.hypot(x - 10, y - 20) - 5) < 1e-9 for x, y in r.vertices())
    e = XYPolygon.from_spec("format=ellipse,x=0,y=0,major=40,minor=20,degs=0,pts=12")
    assert e.size() == 12 and abs(max(e.vx) - 20) < 1e-9 and abs(max(e.vy) - 10) < 1e-9
    w = XYPolygon.from_spec("format=wedge,x=0,y=0,lang=0,rang=90,range=10,pts=3")
    assert w.vertices()[0] == (0, 0) and w.size() == 5
    rw = XYPolygon.from_spec("format=rangewedge,x=0,y=0,lang=0,rang=90,range_min=5,range_max=10,pts=2")
    assert rw.size() == 6
    py = XYPolygon.from_spec("format=pylon,x1=0,y1=0,x2=0,y2=100,axis_pad=5,perp_pad=2")
    assert py.size() == 4 and abs(min(py.vy) + 5) < 1e-9 and abs(max(py.vy) - 105) < 1e-9
    sr = XYPolygon.from_spec("radial: 0, 0, 10, 4, 0, mylabel")
    assert sr.size() == 4 and sr.label == "mylabel"
    kr = XYPolygon.from_spec("radial:: x=0,y=0,radius=10,pts=6")
    assert kr.size() == 6
    bad = XYPolygon.from_spec("format=radial,x=0,y=0")
    assert not bad.valid()
    ov = XYPolygon.from_spec("format=oval,x=0,y=0,rad=5,len=20,ang=90")
    assert ov.size() > 20


def test_seglr():
    s = XYSeglr.from_spec("pts={0.0,0.0:5.0,5.0:20.0,5.0},ray=45.0,label=foo,ray_len=5,head_size=3")
    assert s.size() == 3 and s.ray == 45 and s.ray_len == 5
    ex, ey = s.ray_end()
    assert abs(ex - (20 + 5 * math.sin(math.radians(45)))) < 1e-9
    assert s.get_spec() == "pts={0.0,0.0:5.0,5.0:20.0,5.0},ray=45.0,label=foo,ray_len=5,head_size=3"


def test_circle_marker_vector():
    c = XYCircle.from_spec("x=20,y=-30,radius=40,vertices=24,label=c1,fill_color=blue,fill_transparency=0.3")
    assert c.valid() and c.vertices == 24 and c.fill_transparency == 0.3
    assert c.get_spec() == "x=20,y=-30,radius=40,vertices=24,label=c1,fill_color=blue,fill_transparency=0.3"
    assert not XYCircle.from_spec("x=1,y=2").valid()
    m = XYMarker.from_spec("xpos=4,ypos=2,width=5,primary_color=red,secondary_color=blue,type=gateway,label=base")
    assert m.valid() and m.marker_type == "gateway" and m.primary_color == "red" and m.width == 5
    k = XYMarker.from_spec("x=0,y=0,type=kelp,colors=green:black")
    assert k.marker_type == "kelp" and k.secondary_color == "black"
    assert XYMarker.from_spec("x=0,y=0,type=bogus").marker_type == "circle"
    v = XYVector.from_spec("x=10,y=20,ang=45,mag=3,head_size=2,label=v1")
    assert v.valid() and abs(v.xdot() - 3 * math.sin(math.radians(45))) < 1e-9
    v2 = XYVector.from_spec("xpos=0,ypos=0,xdot=0,ydot=5")
    assert abs(v2.ang) < 1e-9 and abs(v2.mag - 5) < 1e-9


def test_pulses_arrow_wedge_oval_textbox():
    rp = XYRangePulse.from_spec("x=4,y=2,radius=50,fill=0.25,linger=2,label=one,time=100,duration=5")
    assert rp.valid() and rp.radius_at(102.5) == 25 and abs(rp.fill_at(102.5) - 0.125) < 1e-9
    assert not rp.finished(106) and rp.finished(107.1)
    assert XYRangePulse.from_spec("x=0,y=0").effective_duration() == 15
    cp = XYCommsPulse.from_spec("sx=0,sy=0,tx=100,ty=0,beam_width=10,fill=0.35,label=abe2ben,time=10,duration=3")
    tri = cp.triangle()
    assert tri[0] == (0, 0) and sorted(round(v[1], 9) for v in tri[1:]) == [-5.0, 5.0]
    assert cp.finished(13.5)
    ar = XYArrow.from_spec("ctrx=0,ctry=0,ang=0,bwid=4,blen=20,hwid=10,hlen=10,label=a")
    out = ar.outline()
    assert len(out) == 7 and abs(max(y for _, y in out) - 20) < 1e-9
    wd = XYWedge.from_spec("x=0,y=0,rad_low=20,rad_hgh=50,ang_low=30,ang_hgh=90,label=w")
    assert wd.valid() and len(wd.outline()) > 20
    ov = XYOval.from_spec("x=0,y=0,rad=10,len=40,ang=0,draw_degs=5,label=o1")
    assert ov.valid() and len(ov.vertices()) == 74
    tb = XYTextBox.from_spec('x=10,y=20,msg="line, one",msg="line two",12,mcolor=white,label=tb')
    assert tb.messages == ["line, one", "line two"] and tb.fsize == 12 and tb.mcolor == "white"
    assert XYTextBox.from_spec("x=1,y=2").duration == 1.0


def test_parse_view_dispatch_and_expiry():
    obj = parse_view("VIEW_POINT", "x=1,y=2,label=p,duration=3")
    assert obj.KIND == "point"
    obj.stamp(100.0)
    assert not obj.expired(102.9) and obj.expired(103.1)
    forever = parse_view("VIEW_CIRCLE", "x=1,y=2,radius=3")
    forever.stamp(100.0)
    assert not forever.expired(1e9)
    assert parse_view("NOT_A_VIEW", "x=1") is None
    assert parse_view("MARKER", "x=1,y=2").KIND == "marker"


def test_colors():
    assert colors.parse_color("dark_blue") == colors.parse_color("DarkBlue") == colors.NAMED_COLORS["darkblue"]
    assert colors.parse_color("0.5,0.5,0.5") == (0.5, 0.5, 0.5)
    assert colors.parse_color("0.5:0.5:0.5") == (0.5, 0.5, 0.5)
    assert colors.parse_color("hex:ff,80,00") == (1.0, 128 / 255.0, 0.0)
    assert colors.parse_color("invisible") == "invisible" and colors.parse_color("off") == "invisible"
    assert colors.parse_color("#ff0000") is None
    assert colors.parse_color("notacolor") is None
    assert colors.to_css("red") == "#ff0000" and colors.to_css("red", 0.5) == "rgba(255,0,0,0.500)"
    assert colors.to_css("invisible") == "transparent"
    assert colors.css_to_moos("#FF6720") == "hex:FF,67,20".lower() or colors.css_to_moos("#FF6720") == "hex:FF,67,20"
    assert colors.parse_color("grey05") == (0.05, 0.05, 0.05)
    assert colors.parse_color("macbeige") is not None and colors.parse_color("tomatao") is not None


def test_node_record_parse_aliases_and_spec_order():
    s = ("NAME=alpha,X=51.71,Y=-35.5,SPD=2,HDG=118.8,DEPTH=4.6,LAT=43.82498123,LON=-70.32975512,"
         "TYPE=kayak,COLOR=yellow,GROUP=red,MODE=MODE@ACTIVE:LOITERING,ALLSTOP=clear,INDEX=123,"
         "YAW=-0.4677482,TIME=1252348077.59,LENGTH=4,THRUST_MODE_REVERSE=true,TRAJECTORY={a=1,b=2},"
         "BATT=12.1,TRANSPARENCY=0.5")
    r = NodeRecord.from_spec(s)
    assert r.name == "alpha" and r.depth == 4.6 and r.has("depth") and r.has_latlon() and r.has_xy()
    assert r.index == 123 and r.thrust_mode_reverse and r.trajectory == "a=1,b=2"
    assert r.properties == {"BATT": "12.1"} and r.transparency == 0.5
    assert r.mode == "MODE@ACTIVE:LOITERING"
    assert r.valid()
    out = r.get_spec()
    assert out.startswith("NAME=alpha,X=51.71,Y=-35.5,SPD=2,HDG=118.8,DEP=4.6,LAT=43.82498123,LON=-70.32975512,TYPE=kayak,COLOR=yellow,GROUP=red,MODE=MODE@ACTIVE:LOITERING,ALLSTOP=clear,INDEX=123,THRUST_MODE_REVERSE=true,YAW=")
    assert ",TIME=1252348077.59,TRANSPARENCY=0.5,LENGTH=4,TRAJECTORY={a=1,b=2},BATT=12.1" in out
    sparse = NodeRecord.from_spec("NAME=b,LAT=1,LON=2,SPEED=1,HEADING=90,UTC_TIME=5")
    assert sparse.valid() and not sparse.has_xy() and not sparse.has("depth")
    j = NodeRecord.from_spec('{"NAME":"c","X":"1","Y":"2","SPD":"0","HDG":"0","TIME":"1"}')
    assert j.name == "c" and j.x == 1 and j.valid()
    assert not NodeRecord.from_spec("NAME=d,X=1,Y=2").valid()


def test_vehicle_type_helpers():
    assert normalize_vehicle_type("UUV") == "auv"
    assert normalize_vehicle_type("slocum") == "glider"
    assert normalize_vehicle_type("spurdog") == "ship"
    assert default_vehicle_length("auv") == 3.0 and default_vehicle_length("ship") == 12.0
    assert default_vehicle_length("bcrayx") == 1.5


def test_is_convex_rejects_a_self_intersecting_star():
    star = parse_view("VIEW_POLYGON", "pts={0,10:2,-8:-9,4:9,4:-2,-8}")
    pentagon = parse_view("VIEW_POLYGON", "pts={0,10:9,3:6,-8:-6,-8:-9,3}")
    assert not star.is_convex() and pentagon.is_convex()


def test_node_record_keeps_unknown_fields_like_cpp():
    out = NodeRecord.from_spec("NAME=a,X=1,Y=2,SPD=1,HDG=0,ZEBRA=1,PITCH=12.5,APPLE=2").get_spec()
    assert out.endswith(",APPLE=2,PITCH=12.5,ZEBRA=1")


def test_get_spec_takes_active_by_keyword_only():
    point = parse_view("VIEW_POINT", "x=1,y=2,label=p")
    with pytest.raises(TypeError):
        point.get_spec(False)
    assert "active=false" in point.get_spec(active=False)
    seglist = parse_view("VIEW_SEGLIST", "pts={1.25,2.5:3,4},label=s")
    assert "pts={1.25,2.5:3,4}" in seglist.get_spec(2)
