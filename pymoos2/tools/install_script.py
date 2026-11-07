"""Install a pymoos2 script app.

    python -m pymoos2.tools.install_script --python PY --dest DIR --name pFoo pFoo.py [Foo.py ...]

Writes DIR/pFoo with its #! line set to PY and copies the modules beside it.
"""

import argparse
import os
import shutil
import stat
import sys


def install(python, dest, name, entry, modules):
    os.makedirs(dest, exist_ok=True)
    with open(entry, "r", encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    target = os.path.join(dest, name)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"#!{python}\n")
        f.writelines(lines)
    os.chmod(tmp, os.stat(tmp).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    os.replace(tmp, target)
    for mod in modules:
        shutil.copyfile(mod, os.path.join(dest, os.path.basename(mod)))
    return target


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m pymoos2.tools.install_script", description=__doc__.strip().splitlines()[0])
    ap.add_argument("--python", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("entry")
    ap.add_argument("modules", nargs="*")
    a = ap.parse_args(argv)
    for path in [a.entry] + a.modules:
        if not os.path.isfile(path):
            sys.stderr.write(f"not a file: {path}\n")
            return 1
    install(a.python, a.dest, a.name, a.entry, a.modules)
    return 0


if __name__ == "__main__":
    sys.exit(main())
