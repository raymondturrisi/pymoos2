"""
   NodeWatch — pymoos2 example shoreside app
   Subscribes to NODE_REPORT and serves a simple browser page
   showing a scrolling log of vehicle reports.
"""

import json
import threading
import time
import webbrowser

from flask import Flask, Response

from pymoos2 import AppCastingMOOSApp, ACTable, moos_time
from pymoos2.dtos.contacts.NodeRecord import NodeRecord


class NodeWatch(AppCastingMOOSApp):
    SYNOPSIS = (
        "Subscribes to NODE_REPORT on the shoreside and serves a minimal "
        "web page showing a scrolling log of vehicle state. Demonstrates "
        "pymoos2 with Flask for browser-based monitoring."
    )

    VERSION = "0.1.0"

    SUBSCRIPTIONS = [
        "NODE_REPORT  — vehicle state reports (string, NodeRecord spec)",
    ]

    PUBLICATIONS = []

    EXAMPLE_CONFIG = """\
ProcessConfig = pNodeWatch
{
    AppTick   = 4
    CommsTick = 4

    web_port  = 8081
}"""

    def __init__(self):
        super().__init__()
        self.web_port = 8081
        self.reports = []
        self.reports_lock = threading.Lock()
        self.max_reports = 200
        self.vehicles_seen = set()

    def on_startup(self):
        self.web_port = self.config("web_port", default=8081, type=int)
        self._start_web_server()
        self.report_event(f"Web UI at http://localhost:{self.web_port}")
        webbrowser.open(f"http://localhost:{self.web_port}")

    def register_variables(self):
        self.register("NODE_REPORT")

    def on_new_mail(self, mail):
        for msg in mail:
            if msg.name == "NODE_REPORT":
                nr = NodeRecord.from_spec(msg.string())
                entry = {
                    "time": f"{time.time():.2f}",
                    "name": nr.name,
                    "x": f"{nr.x:.1f}",
                    "y": f"{nr.y:.1f}",
                    "hdg": f"{nr.heading:.0f}",
                    "spd": f"{nr.speed:.1f}",
                    "dep": f"{nr.depth:.1f}",
                }
                self.vehicles_seen.add(nr.name)
                with self.reports_lock:
                    self.reports.insert(0, entry)
                    if len(self.reports) > self.max_reports:
                        self.reports = self.reports[:self.max_reports]

    def iterate(self):
        pass

    def build_report(self):
        self.report(f"Web UI: http://localhost:{self.web_port}")
        self.report(f"Vehicles seen: {len(self.vehicles_seen)}")
        with self.reports_lock:
            n = len(self.reports)
        self.report(f"Reports buffered: {n}")
        self.report("")

        tab = ACTable(["Vehicle", "Last X", "Last Y", "Hdg", "Spd"])
        with self.reports_lock:
            seen = set()
            for r in self.reports:
                if r["name"] not in seen:
                    seen.add(r["name"])
                    tab.add(r["name"], r["x"], r["y"], r["hdg"], r["spd"])
        self.report(tab)
        return True

    def _start_web_server(self):
        app = Flask(__name__, static_folder=None)
        viewer = self

        @app.route("/")
        def index():
            return PAGE_HTML

        @app.route("/api/reports")
        def reports():
            with viewer.reports_lock:
                data = list(viewer.reports)
            return Response(json.dumps(data), mimetype="application/json")

        import logging
        logging.getLogger("werkzeug").setLevel(logging.ERROR)

        t = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=self.web_port,
                                   debug=False, use_reloader=False),
            daemon=True)
        t.start()


PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>pNodeWatch</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#1a1a1a; color:#e0e0e0; font-family:'Menlo','Consolas',monospace; font-size:12px; }
#header { padding:10px 16px; background:#252525; border-bottom:1px solid #333; font-size:14px; font-weight:bold; color:#4CAF50; }
#log { padding:8px 16px; }
.row { padding:2px 0; border-bottom:1px solid #222; display:flex; gap:12px; }
.row:hover { background:#252525; }
.ts { color:#666; width:120px; flex-shrink:0; }
.name { color:#4CAF50; width:80px; flex-shrink:0; font-weight:bold; }
.field { color:#aaa; }
.label { color:#666; }
#status { padding:6px 16px; background:#252525; border-top:1px solid #333; position:fixed; bottom:0; left:0; right:0; color:#666; }
</style>
</head>
<body>
<div id="header">pNodeWatch</div>
<div id="log"></div>
<div id="status">Connecting...</div>
<script>
const log = document.getElementById('log');
const status = document.getElementById('status');
let lastCount = 0;

async function poll() {
    try {
        const r = await fetch('/api/reports');
        const data = await r.json();
        if (data.length === lastCount) return;
        lastCount = data.length;

        log.innerHTML = data.map(r =>
            `<div class="row">` +
            `<span class="ts">${r.time}</span>` +
            `<span class="name">${r.name}</span>` +
            `<span class="field"><span class="label">x=</span>${r.x}</span>` +
            `<span class="field"><span class="label">y=</span>${r.y}</span>` +
            `<span class="field"><span class="label">hdg=</span>${r.hdg}</span>` +
            `<span class="field"><span class="label">spd=</span>${r.spd}</span>` +
            `<span class="field"><span class="label">dep=</span>${r.dep}</span>` +
            `</div>`
        ).join('');

        status.textContent = `${data.length} reports | newest at top`;
    } catch(e) {
        status.textContent = 'Connection lost...';
    }
}
setInterval(poll, 500);
poll();
</script>
</body>
</html>"""
