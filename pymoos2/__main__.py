"""
pymoos2 CLI — application generator and example scaffolding.

Usage:
    python3 -m pymoos2 --GenAppCastingMOOSApp AppName [prefix] [author]
    python3 -m pymoos2 --example
"""

import os
import sys
import stat
import shutil


def main():
    args = sys.argv[1:]

    if not args:
        print_usage()
        sys.exit(1)

    if args[0] == "--GenAppCastingMOOSApp":
        gen_app(args[1:])
    elif args[0] == "--example":
        gen_example()
    else:
        print_usage()
        sys.exit(1)


def print_usage():
    print("pymoos2 — Pure-Python MOOS-IvP application framework")
    print()
    print("Usage:")
    print("  python3 -m pymoos2 --GenAppCastingMOOSApp AppName [prefix] [author]")
    print("  python3 -m pymoos2 --example")
    print()
    print("Options:")
    print("  --GenAppCastingMOOSApp  Generate a new MOOS app with AppCasting support")
    print("  --example               Generate a complete example mission with two pymoos2 apps")


def gen_app(remaining):
    if not remaining:
        print("Error: AppName is required.")
        sys.exit(1)

    app_name = remaining[0]
    prefix = remaining[1] if len(remaining) > 1 else "p"
    author = remaining[2] if len(remaining) > 2 else ""

    full_name = f"{prefix}{app_name}"
    out_dir = os.path.join(os.getcwd(), full_name)

    if os.path.exists(out_dir):
        print(f"Error: directory {full_name}/ already exists.")
        sys.exit(1)

    tmpl_dir = os.path.join(os.path.dirname(__file__), "templates")
    replacements = {
        "{{APP_NAME}}": app_name,
        "{{PREFIX}}": prefix,
        "{{AUTHOR}}": author,
    }

    def render(template_name):
        with open(os.path.join(tmpl_dir, template_name), "r") as f:
            content = f.read()
        for k, v in replacements.items():
            content = content.replace(k, v)
        return content

    os.makedirs(out_dir)

    main_path = os.path.join(out_dir, f"{full_name}.py")
    with open(main_path, "w") as f:
        f.write(render("Main.py.tmpl"))
    _make_executable(main_path)

    with open(os.path.join(out_dir, f"{app_name}.py"), "w") as f:
        f.write(render("App.py.tmpl"))

    with open(os.path.join(out_dir, "CMakeLists.txt"), "w") as f:
        f.write(render("CMakeLists.txt.tmpl"))

    print(f"Generated {full_name}/")
    print(f"  {full_name}/{full_name}.py      — entry point (executable)")
    print(f"  {full_name}/{app_name}.py        — app class (edit this)")
    print(f"  {full_name}/CMakeLists.txt       — CMake install rule")
    print()
    print(f"Next steps:")
    print(f"  1. Edit {app_name}.py — implement on_startup, on_new_mail, iterate, build_report")
    print(f"  2. Add to src/CMakeLists.txt:  ADD_SUBDIRECTORY({full_name})")
    print(f"  3. Build:  cd build && cmake .. && make")


def gen_example():
    cwd = os.getcwd()
    src_dir = os.path.join(cwd, "src")
    missions_dir = os.path.join(cwd, "missions")

    print("pymoos2 --example")
    print("=" * 50)
    print()
    print("You should be in moos-ivp-{your-extend-tree}/ with src/ and missions/")
    print("below your current directory.")
    print()
    print(f"  Current directory: {cwd}")
    print()
    print("This will generate:")
    print()
    print("  Apps (in src/):")
    print("    pWptPulse/     — vehicle app: publishes VIEW_RANGE_PULSE on waypoint changes")
    print("    pNodeWatch/    — shoreside app: web page showing scrolling NODE_REPORT log")
    print()
    print("  Mission (in missions/):")
    print("    alpha_pymoos2/ — ufld_alpha-based mission with both pymoos2 apps wired in")
    print()

    if not os.path.isdir(src_dir):
        print(f"Error: no src/ directory found in {cwd}")
        print("  Run this from the root of a moos-ivp-extend tree.")
        sys.exit(1)
    if not os.path.isdir(missions_dir):
        print(f"Error: no missions/ directory found in {cwd}")
        print("  Run this from the root of a moos-ivp-extend tree.")
        sys.exit(1)

    conflicts = []
    for d in ["src/pWptPulse", "src/pNodeWatch", "missions/alpha_pymoos2"]:
        if os.path.exists(os.path.join(cwd, d)):
            conflicts.append(d)
    if conflicts:
        print("Error: the following already exist:")
        for c in conflicts:
            print(f"  {c}/")
        sys.exit(1)

    resp = input("Proceed? [y/N] ").strip().lower()
    if resp not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    try:
        import flask
    except ImportError:
        print("  pNodeWatch requires flask. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"],
                             stdout=subprocess.DEVNULL)
        print("  flask installed.")

    print()
    example_dir = os.path.join(os.path.dirname(__file__), "templates", "example")

    _copytree(os.path.join(example_dir, "pWptPulse"), os.path.join(src_dir, "pWptPulse"))
    _make_executable(os.path.join(src_dir, "pWptPulse", "pWptPulse.py"))
    print("  Created src/pWptPulse/")

    _copytree(os.path.join(example_dir, "pNodeWatch"), os.path.join(src_dir, "pNodeWatch"))
    _make_executable(os.path.join(src_dir, "pNodeWatch", "pNodeWatch.py"))
    print("  Created src/pNodeWatch/")

    _copytree(os.path.join(example_dir, "alpha_pymoos2"), os.path.join(missions_dir, "alpha_pymoos2"))
    for sh in ["launch.sh", "launch_vehicle.sh", "launch_shoreside.sh", "clean.sh"]:
        _make_executable(os.path.join(missions_dir, "alpha_pymoos2", sh))
    print("  Created missions/alpha_pymoos2/")

    print()
    print("To complete setup, add the following to src/CMakeLists.txt:")
    print()
    print("  ADD_SUBDIRECTORY(pWptPulse)")
    print("  ADD_SUBDIRECTORY(pNodeWatch)")
    print()
    print("Then:")
    print("  1. ./build.sh")
    print("  2. cd missions/alpha_pymoos2")
    print("  3. ./launch.sh 10     (launches at 10x time warp)")
    print("  4. Open http://localhost:8081 to see pNodeWatch")
    print("  5. Hit DEPLOY in pMarineViewer — watch for yellow range pulses at waypoints")


def _copytree(src, dst):
    """Copy a directory tree."""
    shutil.copytree(src, dst)


def _make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


if __name__ == "__main__":
    main()
