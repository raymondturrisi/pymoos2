"""
pymoos2 — Pure-Python MOOS-IvP application framework.
"""

from pymoos2.core.AppCastingMOOSApp import AppCastingMOOSApp
from pymoos2.core.MOOSApp import MOOSApp
from pymoos2.core.MOOSMsg import MOOSMsg
from pymoos2.core.MOOSCommClient import MOOSCommClient
from pymoos2.core.MissionReader import MissionReader
from pymoos2.core.ACTable import ACTable
from pymoos2.core.time import moos_time, moos_local_time, moos_pause

import sys
import signal


def run(app_class, app_name, mission_file):
    """
    Launch a pymoos2 application.
    """
    app = app_class()
    app._initialize(app_name, mission_file)

    def shutdown(sig, frame):
        app._shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        app._run()
    except KeyboardInterrupt:
        app._shutdown()


__all__ = [
    "AppCastingMOOSApp",
    "MOOSApp",
    "MOOSMsg",
    "MOOSCommClient",
    "MissionReader",
    "ACTable",
    "moos_time",
    "moos_local_time",
    "moos_pause",
    "run",
]
