"""Brand assets ship in the package."""

import os
import struct

import pytest

from pymoos2 import assets

EXPECTED = ["favicon.ico", "pymoos2-horizontal-dark.png", "pymoos2-horizontal-dark.svg",
            "pymoos2-horizontal-transparent.svg", "pymoos2-mark-256.png", "pymoos2-mark.svg",
            "pymoos2-wordmark-dark.svg", "pymoos2-wordmark-transparent.svg"]


def test_every_asset_is_listed_and_found():
    assert assets.names() == EXPECTED
    for name in EXPECTED:
        p = assets.path(name)
        assert os.path.isabs(p) and os.path.getsize(p) > 0


def test_unknown_or_path_like_names_are_refused():
    with pytest.raises(FileNotFoundError, match="favicon.ico"):
        assets.path("nope.png")
    with pytest.raises(FileNotFoundError):
        assets.path("../__init__.py")
    with pytest.raises(FileNotFoundError):
        assets.path("__init__.py")


def test_favicon_is_an_ico_with_32_and_64_px():
    with open(assets.path("favicon.ico"), "rb") as f:
        data = f.read()
    reserved, kind, count = struct.unpack_from("<HHH", data)
    assert (reserved, kind) == (0, 1)
    sizes = {(data[6 + 16 * i] or 256) for i in range(count)}
    assert sizes == {32, 64}


def test_pngs_are_pngs_and_svgs_need_no_fonts():
    for name in EXPECTED:
        with open(assets.path(name), "rb") as f:
            data = f.read()
        if name.endswith(".png"):
            assert data.startswith(b"\x89PNG\r\n\x1a\n"), name
        elif name.endswith(".svg"):
            text = data.decode()
            assert text.lstrip().startswith("<svg") and "<title>pymoos2</title>" in text, name
            assert "<text" not in text and "font-family" not in text, name
