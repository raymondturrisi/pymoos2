#!/bin/sh
# ./test.sh            run every test
# ./test.sh --wheel    test the built wheel in a fresh venv
# Other arguments go to pytest.
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
export PYTHONDONTWRITEBYTECODE=1
PYTEST_ARGS="-v -rfEs -p no:cacheprovider"

if [ "$1" = "--wheel" ]; then
    shift
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    mkdir "$TMP/src"
    tar -cf - --exclude .git --exclude build --exclude dist --exclude '*.egg-info' \
        --exclude __pycache__ . | tar -xf - -C "$TMP/src"
    "$PY" -m pip wheel --quiet --no-deps --wheel-dir "$TMP/dist" "$TMP/src"
    "$PY" -m venv "$TMP/venv"
    "$TMP/venv/bin/python" -m pip install --quiet "$TMP"/dist/*.whl pytest numpy
    cp -R tests "$TMP/tests"
    cd "$TMP"
    exec "$TMP/venv/bin/python" -m pytest tests $PYTEST_ARGS "$@"
fi

exec "$PY" -m pytest tests $PYTEST_ARGS "$@"
