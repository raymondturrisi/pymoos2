"""Failure paths: malformed wire data, link errors, bad configuration and
app loop exceptions.
"""

import random
import struct
import threading
import time

import pytest

import pymoos2
from pymoos2 import AppCastingMOOSApp, MOOSApp, MissionReader, run
from pymoos2.core import MOOSCommClient as comm_mod
from pymoos2.core import time as mtime
from pymoos2.core.constants import MSG_NOTIFY, DATA_DOUBLE, DATA_STRING, DATA_BINARY, MAX_TIME_WARP
from pymoos2.core.MOOSCommClient import MOOSCommClient
from pymoos2.core.MOOSCommPkt import pack, unpack, HEADER_SIZE
from pymoos2.core.MOOSMsg import MOOSMsg
from tests.fake_db import FakeDB


def wait_for(pred, timeout=4.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def db():
    d = FakeDB(community="robust")
    yield d
    d.stop()


@pytest.fixture
def fast_retry(monkeypatch):
    monkeypatch.setattr(comm_mod, "RETRY_PERIOD_S", 0.05)


def client(db, **kw):
    c = MOOSCommClient("127.0.0.1", db.port, kw.pop("name", "pRobust"), kw.pop("tick", 50.0))
    c.start()
    assert c.wait_until_connected(5.0)
    return c


def _sample_msgs():
    a = MOOSMsg(MSG_NOTIFY, "NAV_X", val=1.5)
    b = MOOSMsg(MSG_NOTIFY, "NOTE", sval="héllo, wörld", data_type=DATA_STRING)
    c = MOOSMsg(MSG_NOTIFY, "BLOB", sval=bytes(range(256)), data_type=DATA_BINARY)
    d = MOOSMsg(MSG_NOTIFY, "EMPTY", sval="", data_type=DATA_STRING)
    for m in (a, b, c, d):
        m.src, m.src_aux, m.community = "pX", "aux", "abe"
    return [a, b, c, d]


def test_packet_round_trip_preserves_everything():
    msgs = _sample_msgs()
    back = unpack(pack(msgs))
    for m, r in zip(msgs, back):
        assert (r.key, r.data_type, r.val, r.src, r.src_aux, r.community, r.msg_type) == \
               (m.key, m.data_type, m.val, m.src, m.src_aux, m.community, m.msg_type)
        assert r.sval == m.sval and r.time == m.time
    assert back[3].is_string() and back[3].string() == ""


def test_non_utf8_text_survives_a_round_trip():
    raw = b"caf\xe9 \xff\xfe end"
    m = MOOSMsg(MSG_NOTIFY, "LEGACY", sval=raw.decode("utf-8", "surrogateescape"), data_type=DATA_STRING)
    (back,) = unpack(pack([m]))
    assert back.string().encode("utf-8", "surrogateescape") == raw
    assert back.binary_data() == raw


def test_every_truncation_and_corruption_is_a_value_error():
    buf = pack(_sample_msgs())
    for cut in range(len(buf)):
        with pytest.raises(ValueError):
            unpack(buf[:cut])
    rng = random.Random(7)
    for _ in range(3000):
        b = bytearray(buf)
        for _ in range(rng.randint(1, 6)):
            b[rng.randrange(HEADER_SIZE, len(b))] = rng.randrange(256)
        try:
            unpack(bytes(b))
        except ValueError:
            pass


@pytest.mark.parametrize("header", [
    struct.pack("<iiB", 99, 0, 0),
    struct.pack("<iiB", HEADER_SIZE, 0, 1),
    struct.pack("<iiB", HEADER_SIZE, -1, 0),
])
def test_bad_packet_headers(header):
    with pytest.raises(ValueError):
        unpack(header)
    with pytest.raises(ValueError):
        unpack(b"\x00\x01")
    with pytest.raises(ValueError):
        unpack(pack([]) + b"\x00")


def test_message_rejects_unknown_data_type():
    m = MOOSMsg(MSG_NOTIFY, "X", val=1.0)
    raw = bytearray(m.serialize())
    raw[9] = ord("Q")
    with pytest.raises(ValueError):
        MOOSMsg.deserialize(bytes(raw))


def test_client_arguments_are_validated():
    with pytest.raises(ValueError):
        MOOSCommClient(app_name="")
    with pytest.raises(ValueError):
        MOOSCommClient(app_name="x", comm_tick=0)


def test_notify_types(db):
    np = pytest.importorskip("numpy")
    c = client(db)
    c.notify("A", np.float32(1.5))
    c.notify("B", np.int64(7))
    c.notify("C", np.bool_(True))
    c.notify("D", bytearray(b"\x00\x01"))
    for bad in (None, [1, 2], {"a": 1}, object()):
        with pytest.raises(TypeError):
            c.notify("E", bad)
    with pytest.raises(ValueError):
        c.notify("", 1.0)
    assert wait_for(lambda: {"A", "B", "C", "D"} <= set(db.keys_received(MSG_NOTIFY)))
    got = {m.key: m for m in db.msgs_received(MSG_NOTIFY)}
    assert got["A"].is_double() and got["A"].double() == 1.5
    assert got["B"].is_double() and got["B"].double() == 7.0
    assert got["C"].is_string() and got["C"].string() == "true"
    assert got["D"].is_binary() and got["D"].binary_data() == b"\x00\x01"
    c.stop()


def test_garbage_reply_reconnects_and_keeps_working(db, fast_retry):
    c = client(db)
    db.garbage_next = True
    c.notify("BEFORE", 1.0)
    assert wait_for(lambda: db.connections >= 2)
    assert "ValueError" in c.last_error
    assert wait_for(c.is_connected.__bool__ if False else (lambda: c.is_connected))
    c.notify("AFTER", 2.0)
    assert wait_for(lambda: "AFTER" in db.keys_received(MSG_NOTIFY))
    assert c._thread.is_alive()
    c.stop()


def test_rejected_handshake_retries(db, fast_retry):
    db.reject_next = "duplicate name"
    c = MOOSCommClient("127.0.0.1", db.port, "pRobust", 50.0)
    c.start()
    assert c.wait_until_connected(5.0) and db.connections >= 2
    c.stop()


def test_send_failure_requeues_the_mail(db, fast_retry, monkeypatch):
    c = client(db)
    real = c._send_pkt
    calls = {"n": 0}

    def flaky(msgs):
        calls["n"] += 1
        if any(m.key == "PRECIOUS" for m in msgs) and calls.get("failed") is None:
            calls["failed"] = True
            raise OSError("cable unplugged")
        return real(msgs)
    monkeypatch.setattr(c, "_send_pkt", flaky)
    c.notify("PRECIOUS", 42.0)
    assert wait_for(lambda: "PRECIOUS" in db.keys_received(MSG_NOTIFY), 6.0)
    assert db.keys_received(MSG_NOTIFY).count("PRECIOUS") == 1
    c.stop()


def test_start_twice_and_stop_twice(db):
    c = client(db)
    with pytest.raises(RuntimeError):
        c.start()
    c.stop()
    c.stop()


def test_unreachable_db_keeps_trying(fast_retry):
    c = MOOSCommClient("127.0.0.1", 1, "pRobust", 10.0)
    c.start()
    assert not c.wait_until_connected(0.4)
    assert c.last_error and c._thread.is_alive()
    c.stop()


def test_time_warp_validation_and_pause():
    old = mtime.get_moos_time_warp()
    try:
        for bad in (0, -1, MAX_TIME_WARP + 1):
            with pytest.raises(ValueError):
                mtime.set_moos_time_warp(bad)
        mtime.set_moos_time_warp(10)
        assert mtime.get_moos_time_warp() == 10.0
        assert mtime.moos_local_time() == pytest.approx(time.time() * 10, rel=1e-6)
        t0 = time.time()
        mtime.moos_pause(200)
        assert time.time() - t0 < 0.15
        assert mtime.moos_local_time(apply_time_warping=False) == pytest.approx(time.time(), abs=0.05)
        mtime.set_moos_skew(2.5)
        assert mtime.get_moos_skew() == 2.5 and mtime.moos_time() - mtime.moos_local_time() == pytest.approx(2.5, abs=0.01)
    finally:
        mtime.set_moos_time_warp(old)
        mtime.set_moos_skew(0.0)


def test_mission_reader_edge_cases(tmp_path):
    p = tmp_path / "m.moos"
    p.write_text("""MOOSTimeWarp = 2
MOOSTimeWarp = 9              // first one wins for globals
URL = http://example.com/a    // the scheme's // is not a comment
Quote = "a // b"
ProcessConfig = pA
{
  flag = maybe
  on = YES
  apptick = 4 // trailing comment
  stray line without equals
}
ProcessConfig = pB {
  k = v
}
ProcessConfig =
ProcessConfig = pC
oops
""")
    mr = MissionReader(str(p), "pA")
    assert mr.get_value("moostimewarp", type=float) == 2.0
    assert mr.get_value("url") == "http://example.com/a" and mr.get_value("Quote") == '"a // b"'
    assert mr.get_config("flag", default=True, type=bool) is True
    assert mr.get_config("on", type=bool) is True and mr.get_config("apptick", type=int) == 4
    assert mr.get_config("apptick", default=7, type=dict) == 7
    assert mr.get_config_lines("pB") == [("k", "v")] and mr.block_names() == ["pA", "pB", "pC"]
    assert not mr.has_block("pZ") and mr.get_config_values("k", "pB") == ["v"]
    assert any("ignored 'stray line" in w for w in mr.warnings)
    assert any("without a name" in w for w in mr.warnings) and any("expected '{'" in w for w in mr.warnings)
    assert mr.get_global_lines()[0] == ("MOOSTimeWarp", "2") and mr.get_all_globals()["MOOSTimeWarp"] == "2"


class Crashy(AppCastingMOOSApp):
    def __init__(self):
        super().__init__()
        self.n = 0

    def iterate(self):
        self.n += 1
        if self.n == 2:
            raise RuntimeError("boom")
        if self.n >= 30:
            self._running = False

    def build_report(self):
        self.report("line one\nline two")
        self.report_event("an event")
        return True


def _mission(tmp_path, port, extra_global="", extra="", name="pCrashy"):
    p = tmp_path / "targ.moos"
    p.write_text(f"ServerHost = 127.0.0.1\nServerPort = {port}\nCommunity = robust\n{extra_global}\n"
                 f"ProcessConfig = {name}\n{{\n  AppTick = 20\n  CommsTick = 50\n{extra}\n}}\n")
    return str(p)


def test_run_survives_user_exceptions_and_reports_them(db, tmp_path, capsys):
    db.post("APPCAST_REQ", "node=all,app=all,duration=10,key=t,thresh=any")
    run(Crashy, "pCrashy", _mission(tmp_path, db.port), install_signal_handlers=False)
    out = capsys.readouterr().out
    assert "RuntimeError: boom" in out
    assert wait_for(lambda: "EXITED_NORMALLY" in db.keys_received(MSG_NOTIFY))
    casts = [m.string() for m in db.msgs_received(MSG_NOTIFY) if m.key == "APPCAST"]
    assert casts and "1:RuntimeError: boom" in casts[-1] and "run_warning_total=1" in casts[-1]
    assert "messages=line one!@line two!@" in casts[-1] and "an event" in casts[-1]


def test_run_fails_fast_on_a_missing_mission():
    with pytest.raises(FileNotFoundError):
        run(Crashy, "pCrashy", "/no/such/mission.moos", install_signal_handlers=False)


def test_bad_time_warp_in_mission_falls_back_to_one(db, tmp_path, capsys):
    run(Crashy, "pCrashy", _mission(tmp_path, db.port, extra_global="MOOSTimeWarp = 0"), install_signal_handlers=False)
    assert "running at time warp 1" in capsys.readouterr().out
    assert mtime.get_moos_time_warp() == 1.0


def test_debug_file_and_config_helpers(db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class Dbg(MOOSApp):
        def iterate(self):
            self.dbg_print("iter %d", self.m_iteration)
            self.seen = (self.config("answer", type=int), self.global_config("Community"), len(self.config_lines()))
            self._running = False
    app = Dbg()
    assert app.config("x", default=3) == 3 and app.global_config("y", default=4) == 4 and app.config_lines() == []
    app.register("NOOP")
    app.notify("NOOP", 1.0)
    run(lambda: app, "pDbg", _mission(tmp_path, db.port, extra="  debug = true\n  answer = 42", name="pDbg"),
        install_signal_handlers=False)
    assert app.seen == (42, "robust", 4)
    dbg = list(tmp_path.glob("DBG_pDbg_*_DATA.dbg"))
    assert dbg and "iter 1" in dbg[0].read_text()


def test_appcast_bookkeeping():
    app = AppCastingMOOSApp()
    app.m_app_name, app.m_community = "pX", "abe"
    app.set_max_events(2)
    for i in range(5):
        app.report_event(f"e{i}")
    assert app._events[-1].endswith("e4") and len(app._events) == 2
    app.report_run_warning("w")
    app.report_run_warning("w")
    app.report_config_warning("c")
    app.report_config_warning("c")
    s = app.get_appcast_string()
    assert "config_warnings=c" in s and "run_warning_total=2" in s and "run_warnings=2:w" in s
    app.retract_run_warning("w")
    app.retract_run_warning("never")
    assert "run_warning_total=0" in app.get_appcast_string()
    app._handle_appcast_req("node=ben,app=pX,duration=3,key=k1,thresh=any")
    app._handle_appcast_req("node=abe,app=pY,duration=3,key=k2,thresh=any")
    app._handle_appcast_req("node=abe,app=pX,duration=3,thresh=any")
    assert app._appcast_requests == {}
    app._handle_appcast_req("node=all,app=all,duration=bogus,key=k3,thresh=run_warning")
    app._warnings_changed = False
    assert not app._appcast_requested()
    app.report_run_warning("new")
    assert app._appcast_requested()
    app._handle_appcast_req("node=abe,app=pX,duration=-5,key=k4,thresh=odd")
    assert "k4" not in app._appcast_requests or app._appcast_requests["k4"][1] == "any"


def test_package_exports():
    for name in pymoos2.__all__:
        assert hasattr(pymoos2, name), name
    assert pymoos2.__version__ == "1.0.1"


def test_non_string_variable_name_is_refused_on_the_calling_thread():
    client = MOOSCommClient("localhost", 9000, "pTest")
    for bad in (123, None, b"X"):
        with pytest.raises(TypeError):
            client.notify(bad, 1.0)
        with pytest.raises(TypeError):
            client.register(bad)
    assert client._outbox == []


def test_message_ids_wrap_instead_of_overflowing(monkeypatch):
    import itertools
    from pymoos2.core import MOOSMsg as msg_mod
    monkeypatch.setattr(msg_mod, "_ID_COUNTER", itertools.count(2 ** 31 - 1))
    first, second = MOOSMsg(MSG_NOTIFY, "X", val=1.0), MOOSMsg(MSG_NOTIFY, "X", val=2.0)
    assert (first.msg_id, second.msg_id) == (2 ** 31 - 1, 0)
    for m in (first, second):
        back, _ = MOOSMsg.deserialize(m.serialize())
        assert back.msg_id == m.msg_id


@pytest.mark.parametrize("big", ["inf", "-inf", "1e400", "nan"])
def test_parsers_never_raise_on_non_finite_numbers(big):
    from pymoos2.casts import parse_appcast
    from pymoos2.casts.realmcast import parse_realmcast
    from pymoos2.dtos.contacts.NodeRecord import NodeRecord
    from pymoos2.dtos.geometry import parse_view
    parse_appcast(f"proc=p!@#iter={big}!@#node=n!@#run_warning_total={big}!@#run_warnings={big}:w")
    parse_realmcast(f"node=n!Q!proc=p!Q!count={big}!Q!messages=a!Z!")
    rec = NodeRecord.from_spec(f"NAME=a,X={big},Y=2,SPD=1,HDG=0,INDEX={big},LENGTH={big}")
    assert not rec.has("x") or rec.x == rec.x
    for var, spec in [
        ("VIEW_CIRCLE", f"x=0,y=0,radius=5,vertices={big}"),
        ("VIEW_TEXTBOX", f"x=0,y=0,msg=hi,fsize={big}"),
        ("VIEW_TEXTBOX", f"x=0,y=0,msg=hi,{big}"),
        ("VIEW_POLYGON", f"format=radial,x=0,y=0,radius=10,pts={big}"),
        ("VIEW_POLYGON", f"format=ellipse,x=0,y=0,major=10,minor=5,degs=0,pts={big}"),
        ("VIEW_POLYGON", f"format=wedge,x=0,y=0,lang=0,rang=90,range=10,pts={big}"),
        ("VIEW_POLYGON", f"format=rangewedge,x=0,y=0,lang=0,rang=90,range_min=1,range_max=10,pts={big}"),
        ("VIEW_POLYGON", f"radial:0,0,10,{big}"),
        ("VIEW_OVAL", f"x=0,y=0,rad=5,len=10,ang=0,draw_degs={big}"),
    ]:
        parse_view(var, spec)
