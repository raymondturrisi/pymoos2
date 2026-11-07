import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")

ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def fixtures_dir():
    return FIXTURES


@pytest.fixture
def sample_mission():
    return os.path.join(FIXTURES, "targ_sample.moos")


@pytest.fixture
def pmv_plug():
    return os.path.join(FIXTURES, "plug_pMarineViewer.moos")
