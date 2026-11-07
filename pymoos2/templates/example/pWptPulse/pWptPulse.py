#!/usr/bin/env python3
"""
   pWptPulse — pymoos2 example vehicle app
"""

import sys
from pymoos2 import run
from WptPulse import WptPulse

PROC_NAME = "pWptPulse"


def show_help():
    print(
        f"{'=' * 60}\n"
        f"Usage: {PROC_NAME} file.moos [OPTIONS]\n"
        f"{'=' * 60}\n"
        f"\n"
        f"SYNOPSIS:\n"
        f"  {WptPulse.SYNOPSIS}\n"
        f"\n"
        f"Options:\n"
        f"  --alias=<ProcessName>\n"
        f"      Launch {PROC_NAME} with the given process name.\n"
        f"  --example, -e\n"
        f"      Display example MOOS configuration block.\n"
        f"  --help, -h\n"
        f"      Display this help message.\n"
        f"  --interface, -i\n"
        f"      Display MOOS publications and subscriptions.\n"
        f"  --version, -v\n"
        f"      Display release version.\n"
        f"\n"
        f"Note: If argv[2] does not otherwise match a known option,\n"
        f"      then it will be interpreted as a run alias. This is\n"
        f"      to support pAntler launching conventions."
    )


def show_example():
    print(WptPulse.EXAMPLE_CONFIG)


def show_interface():
    subs = "\n".join(f"  {s}" for s in WptPulse.SUBSCRIPTIONS)
    pubs = "\n".join(f"  {p}" for p in WptPulse.PUBLICATIONS)
    print(
        f"{'=' * 60}\n"
        f"Interface for: {PROC_NAME}\n"
        f"{'=' * 60}\n"
        f"\n"
        f"SUBSCRIPTIONS:\n"
        f"{subs}\n"
        f"\n"
        f"PUBLICATIONS:\n"
        f"{pubs}"
    )


def show_version():
    print(f"{PROC_NAME} v{WptPulse.VERSION} (pymoos2)")


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    arg = sys.argv[1]
    if arg in ("--help", "-h"):
        show_help()
        return
    elif arg in ("--example", "-e"):
        show_example()
        return
    elif arg in ("--interface", "-i"):
        show_interface()
        return
    elif arg in ("--version", "-v"):
        show_version()
        return

    mission_file = sys.argv[1]
    app_name = PROC_NAME
    for extra in sys.argv[2:]:
        if extra.startswith("--alias="):
            app_name = extra[len("--alias="):]
        elif not extra.startswith("-"):
            app_name = extra

    run(WptPulse, app_name, mission_file)


if __name__ == "__main__":
    main()
