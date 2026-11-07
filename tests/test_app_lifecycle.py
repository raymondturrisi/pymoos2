import os
import threading
import time

import pytest

from pymoos2 import AppCastingMOOSApp, ACTable
from pymoos2.core.constants import MSG_NOTIFY, MSG_REGISTER
from tests.fake_db import FakeDB


@pytest.fixture
def db():
    d = FakeDB(community="shoreside")
    yield d
    d.stop()


def write_mission(tmp_path, port, extra=""):
    p = tmp_path / "targ.moos"
    p.write_text(f"""
ServerHost = 127.0.0.1
ServerPort = {port}
Community  = shoreside
ProcessConfig = pProbe
{{
  AppTick   = 10
  CommsTick = 50
  {extra}
}}
""")
    return str(p)


class Probe(AppCastingMOOSApp):
    def __init__(self):
        super().__init__()
        self.events = []
        self.iterate_sleep = 0.0
        self.connects = 0
        self.mail_seen = []

    def on_startup(self):
        self.events.append(("startup", "APPCAST_REQ" in self.m_comms._subscriptions))

    def register_variables(self):
        self.connects += 1
        self.register("FOO")

    def on_new_mail(self, mail):
        self.mail_seen.extend(m.key for m in mail)

    def iterate(self):
        if self.iterate_sleep:
            time.sleep(self.iterate_sleep)

    def build_report(self):
        tab = ACTable(["A", "B"])
        tab.add("1", "2")
        self.report(tab)
        return True


def run_app(app, mission, seconds):
    app._initialize("pProbe", mission)
    t = threading.Thread(target=app._run, daemon=True)
    t.start()
    time.sleep(seconds)
    app._running = False
    t.join(timeout=3.0)
    app._shutdown()


def wait_for(pred, timeout=3.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.02)
    return False


def test_hook_order_and_registrations(db, tmp_path):
    app = Probe()
    run_app(app, write_mission(tmp_path, db.port), 0.6)
    assert app.events == [("startup", True)]
    regs = db.keys_received(MSG_REGISTER)
    assert "APPCAST_REQ" in regs and "FOO" in regs
    assert app.connects == 1


def test_appcast_req_is_filtered_and_report_posted(db, tmp_path):
    app = Probe()
    app._initialize("pProbe", write_mission(tmp_path, db.port))
    t = threading.Thread(target=app._run, daemon=True)
    t.start()
    assert wait_for(lambda: app.m_iteration > 2)
    db.post("APPCAST_REQ", "node=shoreside,app=pProbe,duration=3,key=test,thresh=any")
    db.post("BAR", "1")
    assert wait_for(lambda: "BAR" in app.mail_seen)
    assert "APPCAST_REQ" not in app.mail_seen
    assert wait_for(lambda: len([m for m in db.msgs_received(MSG_NOTIFY) if m.key == "APPCAST"]) >= 2)
    app._running = False
    t.join(timeout=3.0)
    app._shutdown()
    casts = [m.string() for m in db.msgs_received(MSG_NOTIFY) if m.key == "APPCAST"]
    s = casts[-1]
    assert s.startswith("proc=pProbe!@#iter=")
    assert "!@#node=shoreside!@#" in s
    assert "\n" not in s
    assert "messages=A  B!@" in s
    assert "!@#events_total=0!@#" in s
    assert "!@#run_warning_total=0!@#" in s


def test_tick_rate_holds_with_slow_iterate(db, tmp_path):
    fast, slow = Probe(), Probe()
    slow.iterate_sleep = 0.02
    run_app(fast, write_mission(tmp_path, db.port), 1.5)
    run_app(slow, write_mission(tmp_path, db.port), 1.5)
    assert slow.m_iteration >= fast.m_iteration - 1


def test_reconnect_calls_on_connect_again(db, tmp_path):
    app = Probe()
    app._initialize("pProbe", write_mission(tmp_path, db.port))
    t = threading.Thread(target=app._run, daemon=True)
    t.start()
    assert wait_for(lambda: app.connects == 1)
    db.drop_connection()
    assert wait_for(lambda: app.connects == 2, timeout=6.0)
    app._running = False
    t.join(timeout=3.0)
    app._shutdown()
