import threading
import time

import pytest

from pymoos2.core.constants import (
    MSG_NOTIFY, MSG_REGISTER, MSG_WILDCARD_REGISTER, MSG_WILDCARD_UNREGISTER,
)
from pymoos2.core.MOOSCommClient import MOOSCommClient, wildcard_spec
from tests.fake_db import FakeDB


@pytest.fixture
def db():
    d = FakeDB(community="fake", skew=0.0)
    yield d
    d.stop()


def make_client(db, tick=50.0):
    c = MOOSCommClient("127.0.0.1", db.port, "pTest", comm_tick=tick)
    c.start()
    assert c.wait_until_connected(5.0)
    return c


def wait_for(pred, timeout=3.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.02)
    return False


def test_wildcard_spec_uses_commas():
    assert wildcard_spec("VIEW_*", "*", 0.0) == "AppPattern=*,VarPattern=VIEW_*,Interval=0"
    assert wildcard_spec("NAV_*", "pHelmIvP", 0.5) == "AppPattern=pHelmIvP,VarPattern=NAV_*,Interval=0.5"


def test_notify_typing(db):
    c = make_client(db)
    c.notify("A", "")
    c.notify("B", True)
    c.notify("C", 3)
    c.notify("D", 2.5)
    c.notify("E", b"\x01")
    c.notify("F", "str")
    assert wait_for(lambda: len(db.msgs_received(MSG_NOTIFY)) >= 6)
    got = {m.key: m for m in db.msgs_received(MSG_NOTIFY)}
    assert got["A"].is_string() and got["A"].string() == ""
    assert got["B"].is_string() and got["B"].string() == "true"
    assert got["C"].is_double() and got["C"].double() == 3.0
    assert got["D"].is_double() and got["D"].double() == 2.5
    assert got["E"].is_binary()
    assert got["F"].is_string() and got["F"].community == "fake"
    c.stop()


def test_register_and_wildcard_reach_db(db):
    c = make_client(db)
    c.register("NAV_X")
    c.wildcard_register("VIEW_*")
    c.wildcard_unregister("VIEW_*")
    assert wait_for(lambda: len(db.msgs_received(MSG_WILDCARD_UNREGISTER)) >= 1)
    regs = db.keys_received(MSG_REGISTER)
    assert "NAV_X" in regs
    wc = db.msgs_received(MSG_WILDCARD_REGISTER)
    assert wc and wc[0].string() == "AppPattern=*,VarPattern=VIEW_*,Interval=0"
    assert wc[0].key == "pTest"
    c.stop()


def test_mail_callback_and_fetch(db):
    c = make_client(db)
    got = threading.Event()
    c.set_mail_callback(got.set)
    db.post("HELLO", "world")
    assert got.wait(3.0)
    mail = c.fetch()
    assert [m.key for m in mail] == ["HELLO"]
    assert mail[0].string() == "world"
    assert c.fetch() == []
    c.stop()


def test_reconnect_replays_and_flags(db):
    c = make_client(db)
    assert c.consume_reconnect() is False
    c.register("NAV_X")
    c.wildcard_register("VIEW_*", "*", 0.0)
    assert wait_for(lambda: "NAV_X" in db.keys_received(MSG_REGISTER))
    before = len(db.msgs_received(MSG_WILDCARD_REGISTER))

    db.drop_connection()
    assert wait_for(lambda: db.connections >= 2, timeout=6.0)
    assert c.wait_until_connected(5.0)
    assert wait_for(lambda: db.keys_received(MSG_REGISTER).count("NAV_X") >= 2, timeout=5.0)
    assert wait_for(lambda: len(db.msgs_received(MSG_WILDCARD_REGISTER)) > before, timeout=5.0)
    assert c.consume_reconnect() is True
    assert c.consume_reconnect() is False
    c.stop()
