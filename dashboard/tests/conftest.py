import json
from pathlib import Path
import pytest
from dashboard.data.loader import ROOT, load_bytes


@pytest.fixture
def receipt():
    def read(name="scaling", phase="phase4"):
        path = ROOT / "docs/validation" / phase / (name + ".json")
        return load_bytes(path.read_bytes(), path.name)
    return read


@pytest.fixture
def raw():
    def read(name="scaling", phase="phase4"):
        return json.loads((ROOT / "docs/validation" / phase / (name + ".json")).read_text())
    return read
