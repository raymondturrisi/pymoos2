"""VIEW_* and NODE_REPORT parse and serialize round trips."""

import math

import pytest

from pymoos2.dtos import VIEW_CLASSES, parse_view, NodeRecord, normalize_vehicle_type, default_vehicle_length
from pymoos2.dtos.geometry import colors

SPECS = {
    "VIEW_POINT": ["x=10.5,y=-3,z=2,trans=0.3,label=wpt,vertex_color=red,vertex_size=4,duration=5",
                   "x=1,y=2,label=p,msg=hello,label_color=white,source=pX,time=12.5"],
    "VIEW_SEGLIST": ["pts={0,0:10,0:20,5},label=route,edge_size=1,edge_color=yellow",
                     "pts={0,0,0,start:10,0:20,5,2.5},tags={0:1:a#1:2:b},label=t"],
    "VIEW_SEGLR": ["pts={0,0:5,5:20,5},ray=45,label=foo,ray_len=5,head_size=3,cpa=2,cpax=1,cpay=1"],
    "VIEW_POLYGON": ["pts={60,-40:60,-160:150,-160:180,-100:150,-40},label=west,edge_color=yellow,fill_color=red,fill_transparency=0.2",
                     "format=radial,x=10,y=20,radius=5,pts=8,label=rad",
                     "format=ellipse,x=0,y=0,major=40,minor=20,degs=30,pts=12,label=e",
                     "format=wedge,x=0,y=0,lang=0,rang=90,range=10,pts=3,label=w",
                     "format=rangewedge,x=0,y=0,lang=0,rang=90,range_min=5,range_max=10,pts=2,label=rw",
                     "format=pylon,x1=0,y1=0,x2=0,y2=100,axis_pad=5,perp_pad=2,label=py",
                     "format=oval,x=0,y=0,rad=5,len=20,ang=90,label=ov"],
    "VIEW_CIRCLE": ["x=20,y=-30,radius=40,vertices=24,label=c1,fill_color=blue,fill_transparency=0.3"],
    "VIEW_MARKER": ["x=4,y=2,width=5,primary_color=red,secondary_color=blue,type=gateway,label=base",
                    "x=0,y=0,type=kelp,colors=green:black,label=k",
                    "x=1,y=1,type=diamond,width=3,color=orange,label=d,msg=note"],
    "VIEW_VECTOR": ["x=10,y=20,ang=45,mag=3,head_size=2,label=v1",
                    "xpos=0,ypos=0,xdot=3,ydot=4,label=vd"],
    "VIEW_RANGE_PULSE": ["x=4,y=2,radius=50,fill=0.25,linger=2,label=one,time=100,duration=5"],
    "VIEW_COMMS_PULSE": ["sx=0,sy=0,tx=100,ty=0,beam_width=10,fill=0.35,label=abe2ben,time=10,duration=3"],
    "VIEW_ARROW": ["ctrx=0,ctry=0,ang=30,bwid=4,blen=20,hwid=10,hlen=10,label=a"],
    "VIEW_WEDGE": ["x=0,y=0,rad_low=20,rad_hgh=50,ang_low=30,ang_hgh=90,label=w"],
    "VIEW_OVAL": ["x=0,y=0,rad=10,len=40,ang=15,draw_degs=5,label=o1"],
    "VIEW_TEXTBOX": ["x=1,y=2,label=tb,msg=line one,msg=line two,fsize=12"],
}


@pytest.mark.parametrize("var,spec", [(v, s) for v, ss in SPECS.items() for s in ss])
def test_spec_is_a_fixed_point(var, spec):
    obj = parse_view(var, spec)
    assert obj is not None and obj.valid(), spec
    s1 = obj.get_spec()
    obj2 = parse_view(var, s1)
    assert obj2.get_spec() == s1
    d = obj.to_dict()
    assert d["kind"] == obj.KIND and d.get("label", obj.label) == obj.label
    erase = parse_view(var, obj.get_spec_inactive())
    assert erase is not None and erase.active is False


@pytest.mark.parametrize("var,spec", [(v, s) for v, ss in SPECS.items() for s in ss])
def test_shape_helpers_give_finite_vertices(var, spec):
    obj = parse_view(var, spec)
    for helper in ("vertices", "outline", "triangle", "ray_end"):
        fn = getattr(obj, helper, None)
        if not callable(fn):
            continue
        pts = fn()
        if pts is None:
            continue
        pts = [pts] if isinstance(pts[0], (int, float)) else pts
        assert all(math.isfinite(c) for p in pts for c in p[:2]), (helper, pts)


def test_every_view_class_has_a_spec_here():
    assert set(VIEW_CLASSES) - {"MARKER"} == set(SPECS)


def test_pulses_animate_and_finish():
    rp = parse_view("VIEW_RANGE_PULSE", SPECS["VIEW_RANGE_PULSE"][0])
    assert rp.radius_at(100.0) <= rp.radius_at(102.0) <= 50.0
    assert 0.0 <= rp.fill_at(103.0) <= 0.25 and not rp.finished(101.0) and rp.finished(1000.0)
    cp = parse_view("VIEW_COMMS_PULSE", SPECS["VIEW_COMMS_PULSE"][0])
    assert len(cp.triangle()) == 3 and cp.fill_at(10.0) <= 0.35 and cp.finished(1000.0)
    assert rp.effective_duration() > 0 and cp.effective_duration() > 0


def test_expiry_and_stamping():
    p = parse_view("VIEW_POINT", "x=1,y=2,label=p,duration=3")
    p.stamp(100.0)
    assert not p.expired(102.0) and p.expired(104.0)
    forever = parse_view("VIEW_CIRCLE", "x=1,y=2,radius=3")
    forever.stamp(0.0)
    assert not forever.expired(1e9)


def test_textbox_messages():
    tb = parse_view("VIEW_TEXTBOX", SPECS["VIEW_TEXTBOX"][0])
    tb.add_msg("three")
    assert 'msg="three"' in tb.get_spec()


def test_colors_table():
    assert colors.is_color("dodger_blue") and colors.is_color("DodgerBlue") and colors.is_color("hex:ff,67,20")
    assert colors.is_color("0.1,0.2,0.3") and colors.is_color("0.1:0.2:0.3") and colors.is_color("invisible")
    assert not colors.is_color("#ff6720") and not colors.is_color("not_a_colour") and not colors.is_color("")
    assert colors.parse_color("hex:ff,00,00") == (1.0, 0.0, 0.0) and colors.parse_color("2,0,0") == (1.0, 0.0, 0.0)
    assert colors.parse_color("hex:zz,00,00") is None and colors.parse_color("1,2") is None
    assert colors.to_css("dodger_blue").startswith("#")


NODE = "NAME=abe,X=10.5,Y=-3.25,SPD=1.2,HDG=270,DEP=2,LAT=42.35,LON=-71.08,TYPE=kayak,COLOR=yellow,MODE=SURVEYING,ALLSTOP=clear,INDEX=3,TIME=1700000000.5,LENGTH=4,GROUP=g1,VSOURCE=nav"


def test_node_report_round_trip_and_policies():
    r = NodeRecord.from_spec(NODE)
    assert r.valid() and r.has_xy() and r.has_latlon() and r.has("depth", "speed")
    s1 = r.get_spec()
    assert NodeRecord.from_spec(s1).get_spec() == s1
    terse = r.get_spec(terse=True)
    assert len(terse) < len(s1) and NodeRecord.from_spec(terse).name == "abe"
    glob = r.get_spec(coord_policy_global=True)
    assert "LAT=" in glob
    d = r.to_dict()
    assert d["name"] == "abe" and d["x"] == 10.5 and d["heading"] == 270.0
    r.set_xy(1.0, 2.0)
    r.set_latlon(42.0, -71.0)
    assert (r.x, r.y, r.lat, r.lon) == (1.0, 2.0, 42.0, -71.0)
    assert r.elapsed_time(1700000010.5) == pytest.approx(10.0)
    assert not NodeRecord.from_spec("X=1,Y=2,TIME=3").valid()
    assert NodeRecord.from_spec("garbage") is not None


def test_vehicle_type_helpers_cover_the_table():
    for t in ("kayak", "heron", "auv", "uuv", "ship", "glider", "mokai", "unknown_thing"):
        n = normalize_vehicle_type(t)
        assert isinstance(n, str) and default_vehicle_length(n) >= 0
