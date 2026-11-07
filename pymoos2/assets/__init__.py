"""Brand assets: favicon, mark, wordmark and lockups.

assets.path(name) returns a file's path; assets.names() lists them.
"""

import os

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))


def names():
    """Every asset file name, sorted."""
    return sorted(f for f in os.listdir(ASSETS_DIR)
                  if not f.startswith(("_", ".")) and os.path.isfile(os.path.join(ASSETS_DIR, f)))


def path(name):
    """Absolute path of one asset."""
    available = names()
    if name not in available:
        raise FileNotFoundError(f"no pymoos2 asset {name!r}; available: {', '.join(available)}")
    return os.path.join(ASSETS_DIR, name)
