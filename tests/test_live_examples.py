"""Example apps against a real MOOSDB; skipped without one."""

import os
import shutil
import socket
import subprocess
import sys
import time

import pytest

from pymoos2.core.MOOSCommClient import MOOSCommClient
from pymoos2.casts import parse_appcast

MOOSDB = shutil.which("MOOSDB") or shutil.which(
    "MOOSDB", path=os.path.expanduser("~/dev/moos/moos-ivp/bin"))
from pymoos2.__main__ import TEMPLATE_DIR

EXAMPLE = os.path.join(TEMPLATE_DIR, "example", "pWptPulse")

pytestmark = pytest.mark.skipif(MOOSDB is None, reason="MOOSDB not on PATH")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_for(pred, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(0.05)
    return False


def test_pwptpulse_runs_against_real_db(tmp_path):
    port = free_port()
    mission = tmp_path / "targ.moos"
    mission.write_text(f"""ServerHost = localhost
ServerPort = {port}
Community  = abe
ProcessConfig = pWptPulse
{{
  AppTick   = 4
  CommsTick = 10
}}
""")
    db = subprocess.Popen([MOOSDB, str(mission)], cwd=str(tmp_path),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = None
    try:
        time.sleep(0.8)
        app = subprocess.Popen([sys.executable, "-B", os.path.join(EXAMPLE, "pWptPulse.py"),
                                str(mission), "pWptPulse"], cwd=EXAMPLE,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        mon = MOOSCommClient("localhost", port, "pMon", comm_tick=20)
        mon.start()
        assert mon.wait_until_connected(5)
        mon.register("APPCAST")
        mon.register("VIEW_RANGE_PULSE")
        time.sleep(1.0)
        inbox = []
        mon.notify("APPCAST_REQ", "node=abe,app=pWptPulse,duration=5,key=test,thresh=any")
        mon.notify("NODE_REPORT_LOCAL", "NAME=abe,X=10,Y=20,SPD=1,HDG=90,DEPTH=0,TYPE=kayak,TIME=1,LENGTH=4")
        mon.notify("WPT_INDEX", 1.0)
        time.sleep(0.8)
        mon.notify("WPT_INDEX", 2.0)
        assert wait_for(lambda: inbox.extend(mon.fetch()) or
                        any(m.key == "APPCAST" and "proc=pWptPulse" in m.string() for m in inbox)), \
            (app.poll(), app.stderr.read() if app.poll() is not None else "")
        casts = [m for m in inbox if m.key == "APPCAST"]
        ac = parse_appcast(casts[-1].string())
        assert ac.proc == "pWptPulse" and ac.node == "abe"
        assert wait_for(lambda: inbox.extend(mon.fetch()) or any(m.key == "VIEW_RANGE_PULSE" for m in inbox))
        pulse = [m for m in inbox if m.key == "VIEW_RANGE_PULSE"][-1].string()
        assert "x=10" in pulse and "y=20" in pulse
        mon.stop()
    finally:
        if app:
            app.terminate()
            try:
                app.wait(timeout=3)
            except subprocess.TimeoutExpired:
                app.kill()
        db.terminate()
        try:
            db.wait(timeout=3)
        except subprocess.TimeoutExpired:
            db.kill()


def test_pnodewatch_serves_reports_without_extra_packages(tmp_path):
    import json
    import urllib.request
    port, web = free_port(), free_port()
    mission = tmp_path / "targ.moos"
    mission.write_text(f"""ServerHost = localhost
ServerPort = {port}
Community  = shoreside
ProcessConfig = pNodeWatch
{{
  AppTick   = 4
  CommsTick = 10
  web_port  = {web}
}}
""")
    example = os.path.join(TEMPLATE_DIR, "example", "pNodeWatch")
    db = subprocess.Popen([MOOSDB, str(mission)], cwd=str(tmp_path),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = None
    try:
        time.sleep(0.8)
        app = subprocess.Popen([sys.executable, "-B", os.path.join(example, "pNodeWatch.py"), str(mission)],
                               cwd=example, env=dict(os.environ, BROWSER="true"),
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        mon = MOOSCommClient("localhost", port, "pMon", comm_tick=20)
        mon.start()
        assert mon.wait_until_connected(5)

        def reports():
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{web}/api/reports", timeout=1) as r:
                    return json.loads(r.read())
            except OSError:
                return []

        def posted():
            mon.notify("NODE_REPORT", "NAME=abe,X=10,Y=20,SPD=1.5,HDG=90,DEPTH=0,TYPE=kayak,TIME=1,LENGTH=4")
            return any(r["name"] == "abe" and r["x"] == "10.0" for r in reports())

        assert wait_for(posted), app.stderr.read() if app.poll() is not None else ""
        with urllib.request.urlopen(f"http://127.0.0.1:{web}/", timeout=2) as r:
            assert "<title>pNodeWatch</title>" in r.read().decode()
        from pymoos2 import assets
        with urllib.request.urlopen(f"http://127.0.0.1:{web}/favicon.ico", timeout=2) as r:
            assert r.headers["Content-Type"] == "image/x-icon"
            assert r.read() == open(assets.path("favicon.ico"), "rb").read()
        with urllib.request.urlopen(f"http://127.0.0.1:{web}/mark.svg", timeout=2) as r:
            assert r.headers["Content-Type"] == "image/svg+xml" and b"<svg" in r.read()
        mon.stop()
    finally:
        if app:
            app.terminate()
            try:
                app.wait(timeout=3)
            except subprocess.TimeoutExpired:
                app.kill()
        db.terminate()
        try:
            db.wait(timeout=3)
        except subprocess.TimeoutExpired:
            db.kill()
