"""
Entry point for pFrameMonitor.

pAntler runs:   pFrameMonitor <mission.moos> [<alias>]
By hand:        python -m pframemonitor <mission.moos> [--alias=<name>] [-h|-e|-i|-v]
"""

import os
import sys

from pymoos2 import run

from pframemonitor import __version__
from pframemonitor.app import FrameMonitor

PROC_NAME = "pFrameMonitor"


def parse_args(argv):
    """(mission_file, alias, action): action is None or one of help/example/interface/version."""
    flags = {"--help": "help", "-h": "help", "--example": "example", "-e": "example",
             "--interface": "interface", "-i": "interface", "--version": "version", "-v": "version"}
    alias, positionals = PROC_NAME, []
    for arg in argv:
        if arg in flags:
            return None, alias, flags[arg]
        if arg.startswith("--alias="):
            alias = arg[len("--alias="):]
        elif not arg.startswith("-"):
            positionals.append(arg)
    if len(positionals) > 1:
        alias = positionals[1]
    return (positionals[0] if positionals else None), alias, None


def main(argv=None):
    mission, alias, action = parse_args(sys.argv[1:] if argv is None else argv)
    if action == "example":
        print(FrameMonitor.EXAMPLE_CONFIG)
    elif action == "interface":
        print("SUBSCRIPTIONS:\n  " + "\n  ".join(FrameMonitor.SUBSCRIPTIONS))
        print("PUBLICATIONS:\n  " + "\n  ".join(FrameMonitor.PUBLICATIONS))
    elif action == "version":
        print(f"{PROC_NAME} {__version__} (pymoos2)")
    elif action == "help" or mission is None:
        print(f"Usage: {PROC_NAME} file.moos [alias] [--alias=<name>] [-e|-i|-v|-h]\n\n  {FrameMonitor.SYNOPSIS}")
    elif not os.path.isfile(mission):
        sys.stderr.write(f"{PROC_NAME}: mission file not found: {mission}\n")
        return 2
    else:
        run(FrameMonitor, alias, mission)
    return 0


if __name__ == "__main__":
    sys.exit(main())
