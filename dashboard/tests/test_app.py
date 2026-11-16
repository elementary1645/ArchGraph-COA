from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from dashboard.data.loader import ROOT

APP = str(ROOT / "dashboard/app.py")


def start():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    return at


def choose(at, label, value):
    next(s for s in at.selectbox if s.label == label).set_value(value).run()
    assert not at.exception
    return at


@pytest.mark.parametrize("page", ["CPU overview", "CPU performance", "Memory organization", "Cache & locality", "Multicore performance", "Amdahl’s Law", "Experiment explorer"])
def test_pages_smoke(page):
    at = start()
    at.radio(key="navigation").set_value(page).run()
    assert not at.exception
    assert any("ArchGraph" in t.value for t in at.title)


@pytest.mark.parametrize("page,filename", [("CPU performance", "sequential-smoke.json"), ("Memory organization", "memory.json"),
    ("Memory organization", "layouts.json"), ("Cache & locality", "cache-study.json"), ("Cache & locality", "locality-random.json"),
    ("Multicore performance", "kernels.json"), ("CPU overview", "diagnostic.json")])
def test_pages_with_relevant_receipts(page, filename):
    at = start()
    active = next(s for s in at.selectbox if s.label == "Active receipt")
    choice = next(i for i, option in enumerate(active.options) if option.startswith(filename + " ·"))
    active.set_value(choice).run()
    at.radio(key="navigation").set_value(page).run()
    assert not at.exception
    if page == "CPU performance":
        assert any("No usable hardware-counter" in w.value for w in at.warning)
    if page == "Memory organization":
        assert any("Representation accounting" in i.value for i in at.info)


def test_amdahl_interactions_and_overlay():
    at = start()
    at.radio(key="navigation").set_value("Amdahl’s Law").run()
    next(s for s in at.slider if s.label == "Assumed parallelizable fraction").set_value(.5).run()
    next(c for c in at.checkbox if c.label.startswith("Overlay compatible")).set_value(True).run()
    assert not at.exception
    assert any("THEORETICAL MODEL" in i.value for i in at.info)
    assert any(m.value == "1.778×" for m in at.metric)


def test_empty_state_and_theory_without_receipts():
    at = start()
    at.checkbox(key="demo").set_value(False).run()
    assert not at.exception
    assert any("No validated measurements" in i.value for i in at.info)
    at.radio(key="navigation").set_value("Amdahl’s Law").run()
    assert not at.exception
    assert any("THEORETICAL MODEL" in i.value for i in at.info)


def test_metadata_filtering():
    at = start()
    choose(at, "Experiment type", "locality")
    at.radio(key="navigation").set_value("Cache & locality").run()
    assert not at.exception
    assert at.multiselect
    pattern = next(s for s in at.multiselect if s.label == "Access pattern")
    pattern.set_value([]).run()
    assert not at.exception
    assert any("No compatible numerical" in i.value for i in at.info)


def test_upload_valid_invalid_and_csv():
    at = start()
    at.checkbox(key="demo").set_value(False).run()
    uploader = at.get("file_uploader")[0]
    # Streamlit 1.67 supports uploads in AppTest; older allowed releases may not.
    if not hasattr(uploader, "upload"):
        pytest.skip("Installed AppTest has no file upload API; byte-loader tests cover import paths")
    uploader.upload("broken.json", b"{", "application/json").run()
    assert not at.exception and at.error
    uploader.upload("scaling.json", (ROOT / "docs/validation/phase4/scaling.json").read_bytes(), "application/json").run()
    assert not at.exception
    at.radio(key="navigation").set_value("Multicore performance").run()
    assert not at.exception
    uploader = at.get("file_uploader")[0]
    uploader.upload("scaling.csv", (ROOT / "docs/validation/phase4/scaling.csv").read_bytes(), "text/csv").run()
    assert not at.exception
