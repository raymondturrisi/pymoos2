"""pymoos2 command line.

    python3 -m pymoos2 --GenAppCastingMOOSApp AppName [prefix] [author]
    python3 -m pymoos2 --GenPackageApp AppName [prefix] [author] [--web]
    python3 -m pymoos2 --example
    python3 -m pymoos2 --cmake-block
    python3 -m pymoos2 --cmake-dir
"""

import os
import re
import sys
import stat
import shutil

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
CMAKE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cmake")
EXAMPLE_APPS = ("pWptPulse", "pNodeWatch", "pFrameMonitor")
WEB_ASSETS = ("favicon.ico", "pymoos2-mark.svg")


def cmake_block():
    """The lines a tree's top-level CMakeLists.txt needs once to build pymoos2 apps."""
    with open(os.path.join(CMAKE_DIR, "find_pymoos2.cmake.txt"), "r") as f:
        return f.read().rstrip("\n")


def tree_finds_pymoos2(tree_root):
    """True when tree_root/CMakeLists.txt already calls find_package(PyMOOS2 ...)."""
    path = os.path.join(tree_root, "CMakeLists.txt")
    if not os.path.isfile(path):
        return False
    with open(path, "r", errors="replace") as f:
        return re.search(r"find_package\s*\(\s*PyMOOS2\b", f.read(), re.IGNORECASE) is not None


def print_toplevel_step(tree_root):
    """Print the top-level CMake block unless the tree already has it."""
    top = os.path.join(tree_root, "CMakeLists.txt")
    if tree_finds_pymoos2(tree_root):
        print(f"  {top} already finds pymoos2.")
        return
    print(f"  Once per tree: paste this into {top},")
    print("  next to find_package(MOOS ...) and before ADD_SUBDIRECTORY(src):")
    print()
    for line in cmake_block().splitlines():
        print(f"    {line}")
    print()


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        print_usage()
        return 1

    if args[0] == "--GenAppCastingMOOSApp":
        return gen_app(args[1:])
    if args[0] == "--GenPackageApp":
        return gen_package_app(args[1:])
    if args[0] == "--example":
        return gen_example()
    if args[0] == "--cmake-dir":
        print(CMAKE_DIR)
        return 0
    if args[0] == "--cmake-block":
        print(cmake_block())
        return 0
    if args[0] in ("--version", "-v"):
        from pymoos2 import __version__
        print(f"pymoos2 {__version__}")
        return 0
    print_usage()
    return 1


def print_usage():
    print("pymoos2 — Pure-Python MOOS-IvP application framework")
    print()
    print("Usage:")
    print("  python3 -m pymoos2 --GenAppCastingMOOSApp AppName [prefix] [author]")
    print("  python3 -m pymoos2 --GenPackageApp AppName [prefix] [author] [--web]")
    print("  python3 -m pymoos2 --example")
    print("  python3 -m pymoos2 --cmake-block")
    print("  python3 -m pymoos2 --cmake-dir")
    print()
    print("Options:")
    print("  --GenAppCastingMOOSApp  Script app: pFoo.py + Foo.py copied into bin/ by CMake")
    print("  --GenPackageApp         Package app: pFoo/pfoo/ run in place through a bin/ launcher,")
    print("                          installable with `make install`; --web adds static/ and web checks")
    print("  --example               Add three example apps to src/ and a mission to missions/")
    print("  --cmake-block           Print the lines a tree's top-level CMakeLists.txt needs once")
    print("  --cmake-dir             Print the directory of PyMOOS2Config.cmake (used by that block)")


def _render(template_name, replacements):
    with open(os.path.join(TEMPLATE_DIR, template_name), "r") as f:
        content = f.read()
    for k, v in replacements.items():
        content = content.replace(k, v)
    return content


def _write(path, content, executable=False):
    with open(path, "w") as f:
        f.write(content)
    if executable:
        _make_executable(path)


def gen_app(remaining):
    if not remaining:
        print("Error: AppName is required.")
        return 1

    app_name = remaining[0]
    prefix = remaining[1] if len(remaining) > 1 else "p"
    author = remaining[2] if len(remaining) > 2 else ""

    full_name = f"{prefix}{app_name}"
    out_dir = os.path.join(os.getcwd(), full_name)

    if os.path.exists(out_dir):
        print(f"Error: directory {full_name}/ already exists.")
        return 1

    replacements = {"{{APP_NAME}}": app_name, "{{PREFIX}}": prefix, "{{AUTHOR}}": author}

    os.makedirs(out_dir)
    _write(os.path.join(out_dir, f"{full_name}.py"), _render("Main.py.tmpl", replacements), executable=True)
    _write(os.path.join(out_dir, f"{app_name}.py"), _render("App.py.tmpl", replacements))
    _write(os.path.join(out_dir, "CMakeLists.txt"), _render("CMakeLists.txt.tmpl", replacements))

    print(f"Generated {full_name}/")
    print(f"  {full_name}/{full_name}.py      — entry point (executable)")
    print(f"  {full_name}/{app_name}.py        — app class (edit this)")
    print(f"  {full_name}/CMakeLists.txt       — one call: pymoos2_add_script_app(...)")
    print()
    print("Next steps:")
    print(f"  1. Edit {app_name}.py — implement on_startup, on_new_mail, iterate, build_report")
    print(f"  2. Add to src/CMakeLists.txt:  ADD_SUBDIRECTORY({full_name})")
    print_toplevel_step(os.path.dirname(os.getcwd()))
    print("  3. Build the tree as usual (./build.sh); bin/ gets the app")
    return 0


def package_name_for(full_name):
    """Python package name for an app: lowercase, non-identifier characters become '_'."""
    name = re.sub(r"[^0-9a-zA-Z_]", "_", full_name).lower()
    if name[0].isdigit():
        name = "_" + name
    return name


def gen_package_app(remaining):
    web = "--web" in remaining
    remaining = [a for a in remaining if a != "--web"]
    if not remaining:
        print("Error: AppName is required.")
        return 1

    app_name = remaining[0]
    prefix = remaining[1] if len(remaining) > 1 else "p"
    author = remaining[2] if len(remaining) > 2 else ""
    full_name = f"{prefix}{app_name}"
    pkg_name = package_name_for(full_name)
    out_dir = os.path.join(os.getcwd(), full_name)

    if os.path.exists(out_dir):
        print(f"Error: directory {full_name}/ already exists.")
        return 1

    replacements = {
        "{{APP_NAME}}": app_name,
        "{{PREFIX}}": prefix,
        "{{AUTHOR}}": author,
        "{{PKG_NAME}}": pkg_name,
        "{{REQUIRES}}": " REQUIRES fastapi uvicorn" if web else "",
    }

    pkg_dir = os.path.join(out_dir, pkg_name)
    os.makedirs(pkg_dir)
    _write(os.path.join(out_dir, "CMakeLists.txt"), _render("pkg/CMakeLists.txt.tmpl", replacements))
    _write(os.path.join(pkg_dir, "__init__.py"), _render("pkg/__init__.py.tmpl", replacements))
    _write(os.path.join(pkg_dir, "__main__.py"), _render("pkg/__main__.py.tmpl", replacements))
    _write(os.path.join(pkg_dir, "app.py"), _render("pkg/app.py.tmpl", replacements))
    if web:
        static_dir = os.path.join(pkg_dir, "static")
        os.makedirs(static_dir)
        _write(os.path.join(static_dir, "index.html"), _render("pkg/static_index.html.tmpl", replacements))
        from pymoos2 import assets
        for name in WEB_ASSETS:
            shutil.copyfile(assets.path(name), os.path.join(static_dir, name))

    print(f"Generated {full_name}/")
    print(f"  {full_name}/CMakeLists.txt         — one call: pymoos2_add_package_app(...)")
    print(f"  {full_name}/{pkg_name}/__main__.py   — entry point: mission file, --alias=, -h -e -i -v")
    print(f"  {full_name}/{pkg_name}/app.py        — app class (edit this)")
    if web:
        print(f"  {full_name}/{pkg_name}/static/       — web assets (index.html, favicon, mark), served in place")
    print()
    print("Next steps:")
    print(f"  1. Edit {pkg_name}/app.py")
    print(f"  2. Add to src/CMakeLists.txt:  ADD_SUBDIRECTORY({full_name})")
    print_toplevel_step(os.path.dirname(os.getcwd()))
    print("  3. Build the tree as usual (./build.sh); bin/ gets a launcher that runs the package in place")
    return 0


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
    print("    pWptPulse/     — vehicle script app: publishes VIEW_RANGE_PULSE on waypoint changes")
    print("    pNodeWatch/    — shoreside script app: web page of NODE_REPORT traffic")
    print("    pFrameMonitor/ — vehicle package app: subpackages, packaged data, tests, install rules;")
    print("                     publishes local frame distortion at the vehicle")
    print()
    print("  Mission (in missions/):")
    print("    alpha_pymoos2/ — ufld_alpha-based mission with the pymoos2 apps wired in")
    print()

    if not os.path.isdir(src_dir):
        print(f"Error: no src/ directory found in {cwd}")
        print("  Run this from the root of a moos-ivp-extend tree.")
        return 1
    if not os.path.isdir(missions_dir):
        print(f"Error: no missions/ directory found in {cwd}")
        print("  Run this from the root of a moos-ivp-extend tree.")
        return 1

    conflicts = []
    for d in [f"src/{a}" for a in EXAMPLE_APPS] + ["missions/alpha_pymoos2"]:
        if os.path.exists(os.path.join(cwd, d)):
            conflicts.append(d)
    if conflicts:
        print("Error: the following already exist:")
        for c in conflicts:
            print(f"  {c}/")
        return 1

    resp = input("Proceed? [y/N] ").strip().lower()
    if resp not in ("y", "yes"):
        print("Aborted.")
        return 0

    print()
    example_dir = os.path.join(TEMPLATE_DIR, "example")

    for app in EXAMPLE_APPS:
        dst = os.path.join(src_dir, app)
        _copytree(os.path.join(example_dir, app), dst)
        entry = os.path.join(dst, f"{app}.py")
        if os.path.isfile(entry):
            _make_executable(entry)
        print(f"  Created src/{app}/")

    _copytree(os.path.join(example_dir, "alpha_pymoos2"), os.path.join(missions_dir, "alpha_pymoos2"))
    for sh in ["launch.sh", "launch_vehicle.sh", "launch_shoreside.sh", "clean.sh"]:
        _make_executable(os.path.join(missions_dir, "alpha_pymoos2", sh))
    print("  Created missions/alpha_pymoos2/")

    print()
    print("To finish:")
    print("  Add to src/CMakeLists.txt, beside your other apps:")
    for app in EXAMPLE_APPS:
        print(f"    ADD_SUBDIRECTORY({app})")
    print_toplevel_step(cwd)
    print("Then:")
    print("  1. ./build.sh")
    print("  2. cd missions/alpha_pymoos2")
    print("  3. ./launch.sh 10     (launches at 10x time warp)")
    print("  4. Open http://localhost:8081 to see pNodeWatch")
    print("  5. Hit DEPLOY in pMarineViewer — watch for yellow range pulses at waypoints;")
    print("     uMAC shows pFrameMonitor's distortion table, FRAME_DISTORTION carries the numbers")
    print("  Install elsewhere:  cmake --install build --prefix <dir>")
    return 0


def _copytree(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


if __name__ == "__main__":
    sys.exit(main())
