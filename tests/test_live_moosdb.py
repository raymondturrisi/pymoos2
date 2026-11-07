"""Smoke tests against a real MOOSDB; skipped without one."""

import os
import shutil
import socket
import subprocess
import time

import pytest

from pymoos2.core.MOOSCommClient import MOOSCommClient

MOOSDB = shutil.which("MOOSDB") or shutil.which(
    "MOOSDB", path=os.path.expanduser("~/dev/moos/moos-ivp/bin"))

pytestmark = pytest.mark.skipif(MOOSDB is None, reason="MOOSDB not on PATH")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def moosdb(tmp_path):
    port = free_port()
    mission = tmp_path / "db.moos"
    mission.write_text(f"ServerHost = localhost\nServerPort = {port}\nCommunity = livetest\n")
    proc = subprocess.Popen([MOOSDB, str(mission)], cwd=str(tmp_path),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    yield port
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def wait_for(pred, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.02)
    return False


def test_wildcard_registration_delivers_mail(moosdb):
    sub = MOOSCommClient("localhost", moosdb, "pSub", comm_tick=20)
    pub = MOOSCommClient("localhost", moosdb, "pPub", comm_tick=20)
    sub.start(); pub.start()
    assert sub.wait_until_connected(5) and pub.wait_until_connected(5)
    assert sub.community == "livetest"
    sub.wildcard_register("VIEW_*", "*", 0.0)
    time.sleep(0.3)
    inbox = []
    pub.notify("VIEW_POINT", "x=1,y=2,label=a")
    pub.notify("NOT_A_VIEW", "ignored")
    pub.notify("VIEW_POLYGON", "pts={0,0:1,0:1,1},label=b")
    assert wait_for(lambda: inbox.extend(sub.fetch()) or len(inbox) >= 2)
    keys = sorted(m.key for m in inbox)
    assert keys == ["VIEW_POINT", "VIEW_POLYGON"]
    assert all(m.src == "pPub" and m.community == "livetest" for m in inbox)
    sub.stop(); pub.stop()


def test_empty_string_and_bool_arrive_as_strings(moosdb):
    sub = MOOSCommClient("localhost", moosdb, "pSub2", comm_tick=20)
    pub = MOOSCommClient("localhost", moosdb, "pPub2", comm_tick=20)
    sub.start(); pub.start()
    assert sub.wait_until_connected(5) and pub.wait_until_connected(5)
    sub.register("EMPTY"); sub.register("FLAG")
    time.sleep(0.3)
    pub.notify("EMPTY", "")
    pub.notify("FLAG", True)
    inbox = []
    assert wait_for(lambda: inbox.extend(sub.fetch()) or len(inbox) >= 2)
    got = {m.key: m for m in inbox}
    assert got["EMPTY"].is_string() and got["EMPTY"].string() == ""
    assert got["FLAG"].is_string() and got["FLAG"].string() == "true"
    sub.stop(); pub.stop()
