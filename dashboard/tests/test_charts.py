import pytest
from dashboard.charts import cpu, memory, locality, scaling, amdahl
from dashboard.data.transform import trial_rows, memory_rows, scaling_points
from dashboard.data.validation import DataError


def test_charts_handle_empty():
    assert cpu.wall_times([]) is None
    assert cpu.counters([], "ipc") is None
    assert memory.footprint([]) is None
    assert locality.locality([]) is None
    assert scaling.scaling([], "speedup") is None


def test_real_time_and_scaling_figures(receipt):
    ds = receipt()
    figure = scaling.scaling(scaling_points(ds), "speedup")
    assert figure.layout.yaxis.title.text == "Same-algorithm speedup"
    assert list(figure.data[0].y)[0] == 1
    assert len(scaling.individual(trial_rows(ds)).data) > 0
    assert cpu.wall_times(trial_rows(ds)) is not None


def test_locality_markers_are_only_metadata(receipt):
    ds = receipt("cache-study", "phase5/receipts")
    f = locality.locality(trial_rows(ds), ds.raw["cache_info"]["entries"])
    assert "capacity markers are metadata" in f.layout.title.text
    assert all("reported capacity" in a.text for a in f.layout.annotations)


def test_memory_chart_uses_estimates(receipt):
    ds = receipt("memory", "phase5/receipts")
    fig = memory.footprint(memory_rows(ds))
    assert "not additive" in fig.layout.title.text
    assert fig.layout.barmode == "group"


def test_theory_label_and_optional_overlay(receipt):
    points = scaling_points(receipt())
    fig = amdahl.curve(.95, 8, 2, points)
    assert "theoretical" in fig.layout.title.text
    assert list(fig.data[0].y)[0] == 1
    assert "observations" in fig.data[2].name
    with pytest.raises(DataError):
        amdahl.curve(.95, 2, 8)
