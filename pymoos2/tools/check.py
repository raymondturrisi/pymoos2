"""Build-time check for pymoos2 apps.

    python -m pymoos2.tools.check <dir> [--require mod ...]

Parses every .py and imports each required module; exits non-zero on
failure.
"""

import ast
import importlib
import os
import sys


def check_syntax(root):
    bad = 0
    for dirpath, _, files in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    ast.parse(f.read(), filename=path)
            except SyntaxError as e:
                sys.stderr.write(f"{path}:{e.lineno}: {e.msg}\n")
                bad += 1
    return bad


def check_imports(modules):
    bad = 0
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception as e:
            sys.stderr.write(f"cannot import '{mod}' with {sys.executable}: {e}\n")
            bad += 1
    return bad


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    root = argv[0]
    modules = []
    if "--require" in argv:
        modules = argv[argv.index("--require") + 1:]
    failures = 0
    if not os.path.isdir(root):
        sys.stderr.write(f"not a directory: {root}\n")
        failures += 1
    else:
        failures += check_syntax(root)
    failures += check_imports(modules)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
