# pymoos2

Pure-Python MOOS-IvP application framework. Write MOOS apps in Python with full AppCasting, wire protocol, and pAntler integration.

## Install

```bash
pip install pymoos2
```

## Quick Start

Generate a new app:

```bash
cd moos-ivp-myproject/src
python3 -m pymoos2 --GenAppCastingMOOSApp MyApp p "Your Name"
```

This creates `pMyApp/` with a ready-to-edit Python MOOS app that:
- Connects to MOOSDB over the native wire protocol
- Supports AppCasting (shows up in uMAC/pMarineViewer)
- Reads ProcessConfig from `.moos` files
- Installs to `bin/` via CMake alongside C++ apps
- Responds to `ktm` shutdown signals
- Handles time warp correctly

## Example Mission

Generate a complete working example with two apps and a mission:

```bash
cd moos-ivp-myproject
python3 -m pymoos2 --example
```

## Writing an App

```python
from pymoos2 import AppCastingMOOSApp, ACTable

class MyApp(AppCastingMOOSApp):

    def on_startup(self):
        self.radius = self.config("radius", default=50.0, type=float)
        self.register("NAV_X")
        self.register("NAV_Y")

    def on_new_mail(self, mail):
        for msg in mail:
            if msg.name == "NAV_X":
                self.nav_x = msg.double()

    def iterate(self):
        self.notify("MY_OUTPUT", self.nav_x * 2.0)

    def build_report(self):
        tab = ACTable(["Variable", "Value"])
        tab.add("NAV_X", f"{self.nav_x:.2f}")
        self.report(tab)
        return True
```

## Features

- Pure Python — no C++ compilation, no pybind11
- Full MOOS wire protocol (binary TCP, same as C++ clients)
- AppCasting and RealmCasting support
- Time warp support (`MOOSTimeWarp`)
- `ktm` (kill the moos) UDP multicast listener
- Mission file parsing (ProcessConfig blocks, global params)
- Geometry DTOs for all VIEW_* types (XYPoint, XYPolygon, XYCircle, etc.)
- NodeRecord parsing
- `py_compile` syntax checking at build time
- Works with pAntler — shebang'd scripts in `bin/`

## Requirements

- Python >= 3.8
- MOOSDB running (from moos-ivp)
- No other dependencies for core functionality
- `flask` for web-based viewer apps (optional)
