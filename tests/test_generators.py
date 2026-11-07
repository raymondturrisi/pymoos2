"""Generators and the CMake build, install and relocation."""

import os
import shutil
import stat
import subprocess
import sys

import pytest

from pymoos2 import assets
from pymoos2.__main__ import main as cli_main, package_name_for, cmake_block, CMAKE_DIR, EXAMPLE_APPS, TEMPLATE_DIR

PY = sys.executable
CMAKE = shutil.which("cmake")
CXX = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
needs_cmake = pytest.mark.skipif(CMAKE is None or CXX is None, reason="cmake or a C++ compiler not available")
REPO_README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")


def run(cmd, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("timeout", 120)
    return subprocess.run(cmd, **kw)


def test_package_name_for():
    assert package_name_for("uMy_App2") == "umy_app2"
    assert package_name_for("pWptPulse") == "pwptpulse"
    assert package_name_for("9lives") == "_9lives"


def test_cli_usage_version_and_cmake_dir(capsys):
    assert cli_main([]) == 1
    assert cli_main(["--bogus"]) == 1
    assert cli_main(["--version"]) == 0
    assert capsys.readouterr().out.startswith("pymoos2 ")
    assert cli_main(["--cmake-dir"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == CMAKE_DIR
    for name in ("PyMOOS2Config.cmake", "PyMOOS2ConfigVersion.cmake", "launcher.sh.in"):
        assert os.path.isfile(os.path.join(out, name)), name
    assert cli_main(["--cmake-block"]) == 0
    block = capsys.readouterr().out
    assert block.strip() == cmake_block() and "find_package(PyMOOS2 QUIET)" in block


def _assert_one_call(cm, call):
    code = [ln for ln in cm.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert code == [call], code
    assert "{{" not in cm


def test_gen_package_app_layout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli_main(["--GenPackageApp", "Probe", "p", "Tester", "--web"]) == 0
    root = tmp_path / "pProbe"
    assert sorted(p.name for p in root.iterdir()) == ["CMakeLists.txt", "pprobe"]
    assert (root / "pprobe" / "__main__.py").is_file() and (root / "pprobe" / "app.py").is_file()
    page = (root / "pprobe" / "static" / "index.html").read_text()
    assert 'href="favicon.ico"' in page and 'src="pymoos2-mark.svg"' in page and "{{" not in page
    for name in ("favicon.ico", "pymoos2-mark.svg"):
        assert (root / "pprobe" / "static" / name).read_bytes() == open(assets.path(name), "rb").read()
    cm = (root / "CMakeLists.txt").read_text()
    _assert_one_call(cm, "pymoos2_add_package_app(NAME pProbe PACKAGE pprobe REQUIRES fastapi uvicorn)")
    assert "Tester" in cm
    assert cli_main(["--GenPackageApp", "Probe"]) == 1
    assert cli_main(["--GenPackageApp"]) == 1


def test_gen_script_app_layout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli_main(["--GenAppCastingMOOSApp", "Thing", "p", "Tester"]) == 0
    root = tmp_path / "pThing"
    assert sorted(p.name for p in root.iterdir()) == ["CMakeLists.txt", "Thing.py", "pThing.py"]
    assert os.access(root / "pThing.py", os.X_OK)
    cm = (root / "CMakeLists.txt").read_text()
    _assert_one_call(cm, "pymoos2_add_script_app(NAME pThing ENTRY pThing.py MODULES Thing.py)")
    src = (root / "pThing.py").read_text()
    assert '--alias=' in src and "webbrowser" not in src
    assert cli_main(["--GenAppCastingMOOSApp", "Thing", "p"]) == 1
    assert cli_main(["--GenAppCastingMOOSApp"]) == 1


def test_generators_print_the_toplevel_block_only_when_missing(tmp_path, monkeypatch, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "CMakeLists.txt").write_text("project(t)\nADD_SUBDIRECTORY(src)\n")
    monkeypatch.chdir(tmp_path / "src")
    assert cli_main(["--GenPackageApp", "A", "p"]) == 0
    assert "find_package(PyMOOS2 QUIET)" in capsys.readouterr().out
    (tmp_path / "CMakeLists.txt").write_text("project(t)\n" + cmake_block() + "\nADD_SUBDIRECTORY(src)\n")
    assert cli_main(["--GenAppCastingMOOSApp", "B", "p"]) == 0
    out = capsys.readouterr().out
    assert "already finds pymoos2" in out and "find_package(PyMOOS2 QUIET)" not in out


def test_readme_shows_the_shipped_block():
    if not os.path.isfile(REPO_README):
        pytest.skip("README not beside the tests (installed copy)")
    with open(REPO_README) as f:
        assert cmake_block() in f.read()


def test_generated_package_entry_point_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli_main(["--GenPackageApp", "Probe", "p"]) == 0
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(tmp_path / "pProbe"), os.environ.get("PYTHONPATH")])))
    out = run([PY, "-m", "pprobe", "--version"], env=env)
    assert out.returncode == 0 and out.stdout.strip() == "pProbe v0.1.0 (pymoos2)"
    assert "ProcessConfig = pProbe" in run([PY, "-m", "pprobe", "-e"], env=env).stdout
    assert "SUBSCRIPTIONS" in run([PY, "-m", "pprobe", "-i"], env=env).stdout
    assert "Usage: pProbe file.moos" in run([PY, "-m", "pprobe"], env=env).stdout
    out = run([PY, "-m", "pprobe", str(tmp_path / "missing.moos")], env=env)
    assert out.returncode == 2 and "mission file not found" in out.stderr


def test_example_refuses_without_tree_and_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli_main(["--example"]) == 1
    (tmp_path / "src").mkdir()
    (tmp_path / "missions").mkdir()
    (tmp_path / "src" / "pFrameMonitor").mkdir()
    assert cli_main(["--example"]) == 1
    assert not (tmp_path / "src" / "pWptPulse").exists()


def test_example_generates_three_apps(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "missions").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert cli_main(["--example"]) == 0
    calls = {"pWptPulse": "pymoos2_add_script_app(NAME pWptPulse ENTRY pWptPulse.py MODULES WptPulse.py)",
             "pNodeWatch": "pymoos2_add_script_app(NAME pNodeWatch ENTRY pNodeWatch.py MODULES NodeWatch.py)",
             "pFrameMonitor": "pymoos2_add_package_app(NAME pFrameMonitor PACKAGE pframemonitor)"}
    for app in EXAMPLE_APPS:
        _assert_one_call((tmp_path / "src" / app / "CMakeLists.txt").read_text(), calls[app])
    assert (tmp_path / "src" / "pFrameMonitor" / "pframemonitor" / "data" / "thresholds.json").is_file()
    assert os.access(tmp_path / "missions" / "alpha_pymoos2" / "launch.sh", os.X_OK)
    assert "pFrameMonitor" in (tmp_path / "missions" / "alpha_pymoos2" / "meta_vehicle.moos").read_text()
    assert not list(tmp_path.rglob("__pycache__"))


def test_checker_reports_syntax_and_imports(tmp_path):
    good = tmp_path / "ok"
    good.mkdir()
    (good / "a.py").write_text("x = 1\n")
    r = run([PY, "-m", "pymoos2.tools.check", str(good), "--require", "pymoos2"])
    assert r.returncode == 0, r.stderr
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "b.py").write_text("def broken(:\n")
    r = run([PY, "-m", "pymoos2.tools.check", str(bad)])
    assert r.returncode == 1 and "b.py:1" in r.stderr
    r = run([PY, "-m", "pymoos2.tools.check", str(good), "--require", "no_such_module_xyz"])
    assert r.returncode == 1 and "no_such_module_xyz" in r.stderr
    r = run([PY, "-m", "pymoos2.tools.check", str(tmp_path / "nope")])
    assert r.returncode == 1 and "not a directory" in r.stderr
    assert run([PY, "-m", "pymoos2.tools.check"]).returncode == 2


def test_install_script_sets_interpreter(tmp_path):
    from pymoos2.tools.install_script import main as install_main
    (tmp_path / "pX.py").write_text("#!/usr/bin/env python3\nimport X\nprint(X.V)\n")
    (tmp_path / "X.py").write_text("V = 'ok'\n")
    dest = tmp_path / "bin"
    assert install_main(["--python", PY, "--dest", str(dest), "--name", "pX",
                         str(tmp_path / "pX.py"), str(tmp_path / "X.py")]) == 0
    text = (dest / "pX").read_text()
    assert text.splitlines()[0] == f"#!{PY}" and text.count("#!") == 1
    assert os.stat(dest / "pX").st_mode & stat.S_IXUSR
    assert run([str(dest / "pX")]).stdout.strip() == "ok"
    assert install_main(["--python", PY, "--dest", str(dest), "--name", "pY", str(tmp_path / "missing.py")]) == 1


def _tree(root, apps, python=PY):
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.10)\nproject(probe CXX)\n"
        f'set(EXECUTABLE_OUTPUT_PATH "{root}/bin")\n\n' + cmake_block() + "\n\nADD_SUBDIRECTORY(src)\n")
    hello = root / "src" / "pHello"
    hello.mkdir(exist_ok=True)
    (hello / "main.cpp").write_text('#include <iostream>\nint main() { std::cout << "pHello" << std::endl; }\n')
    (hello / "CMakeLists.txt").write_text("ADD_EXECUTABLE(pHello main.cpp)\ninstall(TARGETS pHello RUNTIME DESTINATION bin)\n")
    (root / "src" / "CMakeLists.txt").write_text("".join(f"ADD_SUBDIRECTORY({a})\n" for a in ["pHello"] + apps))
    build = root / "build"
    cmd = [CMAKE, "-S", str(root), "-B", str(build)]
    if python:
        cmd.append(f"-DPYMOOS2_PYTHON={python}")
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    r = run(cmd, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return build, r.stdout + r.stderr


def _build(build):
    return run([CMAKE, "--build", str(build)])


def _launcher_python(launcher):
    for line in launcher.read_text().splitlines():
        if line.startswith('PY="${PYMOOS2_PYTHON_OVERRIDE:-'):
            return line[len('PY="${PYMOOS2_PYTHON_OVERRIDE:-'):-2]
    raise AssertionError("no PY= line in " + str(launcher))


def _same(a, b):
    return os.path.samefile(str(a), str(b))


@needs_cmake
def test_cmake_generated_apps_build_install_and_relocate(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    monkeypatch.chdir(tmp_path / "src")
    assert cli_main(["--GenPackageApp", "Probe", "p"]) == 0
    assert cli_main(["--GenAppCastingMOOSApp", "Thing", "p"]) == 0
    build, _ = _tree(tmp_path, ["pProbe", "pThing"])
    r = _build(build)
    assert r.returncode == 0, r.stdout + r.stderr

    assert run([str(tmp_path / "bin" / "pHello")]).stdout.strip() == "pHello"
    launcher = tmp_path / "bin" / "pProbe"
    assert os.access(launcher, os.X_OK) and _same(_launcher_python(launcher), PY)
    assert run([str(launcher), "--version"]).stdout.strip() == "pProbe v0.1.0 (pymoos2)"
    script = tmp_path / "bin" / "pThing"
    assert _same(script.read_text().splitlines()[0][2:], PY) and (tmp_path / "bin" / "Thing.py").is_file()
    assert "pThing v" in run([str(script), "--version"]).stdout

    env = dict(os.environ, PPROBE_LOG_DIR=str(tmp_path / "logs"))
    run([str(launcher), str(tmp_path / "missing.moos")], env=env)
    assert "mission file not found" in (tmp_path / "logs" / "launch.log").read_text()

    prefix = tmp_path / "prefix"
    r = run([CMAKE, "--install", str(build), "--prefix", str(prefix)])
    assert r.returncode == 0, r.stdout + r.stderr
    assert (prefix / "lib" / "pymoos2-apps" / "pProbe" / "pprobe" / "app.py").is_file()
    assert not list(prefix.rglob("__pycache__"))
    assert run([str(prefix / "bin" / "pHello")]).stdout.strip() == "pHello"
    assert run([str(prefix / "bin" / "pProbe"), "--version"]).stdout.strip() == "pProbe v0.1.0 (pymoos2)"
    assert "pThing v" in run([str(prefix / "bin" / "pThing"), "--version"]).stdout

    moved = tmp_path / "moved"
    shutil.move(str(prefix), str(moved))
    r = run([str(moved / "bin" / "pProbe"), "--version"])
    assert r.returncode == 0 and r.stdout.strip() == "pProbe v0.1.0 (pymoos2)"


@needs_cmake
def test_cmake_uses_a_venv_beside_the_tree(tmp_path, monkeypatch):
    tree = tmp_path / "moos-ivp-probe"
    (tree / "src").mkdir(parents=True)
    venv_py = tmp_path / "venv" / "bin" / "python3"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text(f'#!/bin/sh\nexec "{PY}" "$@"\n')
    venv_py.chmod(0o755)
    monkeypatch.chdir(tree / "src")
    assert cli_main(["--GenPackageApp", "Probe", "p"]) == 0
    build, _ = _tree(tree, ["pProbe"], python=None)
    cached = [ln.split("=", 1)[1] for ln in (build / "CMakeCache.txt").read_text().splitlines()
              if ln.startswith("PYMOOS2_PYTHON:")]
    assert len(cached) == 1 and _same(cached[0], venv_py)
    assert _build(build).returncode == 0
    assert _same(_launcher_python(tree / "bin" / "pProbe"), venv_py)


@needs_cmake
def test_cmake_check_fails_the_build_on_errors(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    monkeypatch.chdir(tmp_path / "src")
    assert cli_main(["--GenPackageApp", "Probe", "p"]) == 0
    (tmp_path / "src" / "pProbe" / "pprobe" / "broken.py").write_text("def broken(:\n")
    build, _ = _tree(tmp_path, ["pProbe"])
    r = _build(build)
    assert r.returncode != 0 and "broken.py:1" in (r.stdout + r.stderr)
    assert not (tmp_path / "bin" / "pProbe").exists()


@needs_cmake
def test_cmake_without_pymoos2_skips_python_apps_only(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    monkeypatch.chdir(tmp_path / "src")
    assert cli_main(["--GenPackageApp", "Probe", "p"]) == 0
    assert cli_main(["--GenAppCastingMOOSApp", "Thing", "p"]) == 0
    fake = tmp_path / "fakepy"
    fake.write_text("#!/bin/sh\nexit 1\n")
    fake.chmod(0o755)
    build, out = _tree(tmp_path, ["pProbe", "pThing"], python=str(fake))
    assert "pymoos2 is not importable" in out and "Python apps will not be built" in out
    assert "PYMOOS2_PYTHON:" not in (build / "CMakeCache.txt").read_text()
    r = _build(build)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "bin" / "pHello").is_file()
    assert not (tmp_path / "bin" / "pProbe").exists() and not (tmp_path / "bin" / "pThing").exists()


@needs_cmake
def test_cmake_version_request(tmp_path):
    from pymoos2 import __version__
    (tmp_path / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.10)\nproject(v NONE)\n"
        f'set(PYMOOS2_PYTHON "{PY}")\nset(PyMOOS2_DIR "{CMAKE_DIR}")\n'
        "foreach(req 1.0 1.0.0 1.1 0.2 2.0)\n"
        "  unset(PyMOOS2_FOUND)\n"
        "  find_package(PyMOOS2 ${req} QUIET)\n"
        '  message(STATUS "req=${req} found=${PyMOOS2_FOUND} version=${PyMOOS2_VERSION}")\n'
        "endforeach()\n")
    r = run([CMAKE, "-S", str(tmp_path), "-B", str(tmp_path / "b")])
    assert r.returncode == 0, r.stdout + r.stderr
    found = dict(ln.split("req=")[1].split(" found=") for ln in r.stdout.splitlines() if "req=" in ln)
    assert found["1.0"].startswith(f"1 version={__version__}") and found["1.0.0"].startswith("1")
    assert found["1.1"].startswith("0") and found["0.2"].startswith("0") and found["2.0"].startswith("0")


@needs_cmake
def test_cmake_shipped_examples_build_and_install(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "missions").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert cli_main(["--example"]) == 0
    build, _ = _tree(tmp_path, list(EXAMPLE_APPS))
    r = _build(build)
    assert r.returncode == 0, r.stdout + r.stderr
    for app in ("pHello",) + EXAMPLE_APPS:
        assert os.access(tmp_path / "bin" / app, os.X_OK), app
    for app in EXAMPLE_APPS:
        r = run([str(tmp_path / "bin" / app), "-e"])
        assert r.returncode == 0 and f"ProcessConfig = {app}" in r.stdout, app
    prefix = tmp_path / "prefix"
    assert run([CMAKE, "--install", str(build), "--prefix", str(prefix)]).returncode == 0
    for app in ("pHello",) + EXAMPLE_APPS:
        assert os.access(prefix / "bin" / app, os.X_OK), app
    pkg = prefix / "lib" / "pymoos2-apps" / "pFrameMonitor" / "pframemonitor"
    assert (pkg / "data" / "thresholds.json").is_file()
    assert (pkg / "frames" / "mission.py").is_file() and (pkg / "metrics" / "thresholds.py").is_file()
    assert not (prefix / "lib" / "pymoos2-apps" / "pFrameMonitor" / "tests").exists()
    assert run([str(prefix / "bin" / "pFrameMonitor"), "-e"]).stdout.startswith("ProcessConfig = pFrameMonitor")
    code = ("from pframemonitor.metrics import load_thresholds, DEFAULTS_PATH; "
            "print(DEFAULTS_PATH); print(load_thresholds().scale_ppm)")
    env = dict(os.environ, PYTHONPATH=str(pkg.parent))
    out = run([PY, "-c", code], env=env).stdout.split()
    assert out[0].startswith(str(prefix)) and out[1] == "500.0"


def test_example_package_tests_pass():
    root = os.path.join(TEMPLATE_DIR, "example", "pFrameMonitor")
    r = run([PY, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"], cwd=root,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    shutil.rmtree(os.path.join(root, "tests", "__pycache__"), ignore_errors=True)
    for d in ("pframemonitor", "pframemonitor/frames", "pframemonitor/metrics"):
        shutil.rmtree(os.path.join(root, d, "__pycache__"), ignore_errors=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_checker_in_process(tmp_path, capsys):
    from pymoos2.tools.check import main as check_main
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__" / "junk.py").write_text("def (:\n")
    assert check_main([str(tmp_path / "pkg"), "--require", "json"]) == 0
    (tmp_path / "pkg" / "b.py").write_text("def broken(:\n")
    assert check_main([str(tmp_path / "pkg")]) == 1
    assert check_main([]) == 2
    assert "b.py:1" in capsys.readouterr().err
