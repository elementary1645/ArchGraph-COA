import copy
import csv
import io
import json
import math
from pathlib import Path
import pytest
from dashboard.data.loader import ROOT, load_bytes, load_receipt, catalog, canonical
from dashboard.data.validation import DataError
from dashboard.data.transform import (trial_rows, filter_rows, grouped_timings, counter_rows, memory_rows,
                                     scaling_points, amdahl, compatible, environment_key, locality_comparable)
from dashboard.data.export import selection_json, filtered_csv


def load(value):
    return load_bytes(json.dumps(value).encode(), "result.json")


@pytest.mark.parametrize("entry", catalog(), ids=lambda v: v["path"])
def test_authentic_receipt(entry):
    ds = load_receipt(entry)
    original = json.loads((ROOT / entry["path"]).read_text())
    assert ds.raw == original
    assert "Archived" in ds.origin
    for row in trial_rows(ds):
        assert row["wall_ns"] >= 0


def test_json_bom_and_no_mutation(raw):
    d = raw()
    before = copy.deepcopy(d)
    ds = load_bytes(b"\xef\xbb\xbf" + json.dumps(d).encode(), "../untrusted.json")
    assert ds.name == "untrusted.json"
    rows = trial_rows(ds)
    grouped_timings(rows)
    scaling_points(ds)
    assert ds.raw == before
    assert rows[0]["checksum"] == str(d["trials"][0]["checksum"])


@pytest.mark.parametrize("payload,name", [(b"{}", "a.json"), (b"[]", "a.json"), (b"{", "a.json"),
    (b'{"schema_version":1,"schema_version":1}', "a.json"), (b'{"x":NaN}', "a.json"),
    (b"\xff", "a.json"), (b"x", "a.pkl"), (b"", "a.json"), (b"[" * 100 + b"]" * 100, "a.json")])
def test_malformed(payload, name):
    with pytest.raises(DataError):
        load_bytes(payload, name)


def test_size_limit():
    with pytest.raises(DataError, match="16 MiB"):
        load_bytes(b"x" * (16 * 1024 * 1024 + 1), "a.json")


@pytest.mark.parametrize("mutation", [lambda d: d.update(schema_version=2), lambda d: d.update(verified=False),
    lambda d: d.update(schema="unknown"), lambda d: d.update(warnings=42), lambda d: d.update(environment_diagnostic=[]),
    lambda d: d["trials"][0].update(wall_ns=-1), lambda d: d["trials"][0].update(warmup="false"),
    lambda d: d["trials"][0].update(observed_threads=0), lambda d: d["trials"][0].update(strategy="dijkstra"),
    lambda d: d["summaries"][0].update(median_wall_ns=1), lambda d: d["amdahl"].update(theoretical=False),
    lambda d: d["amdahl"].update(assumed_parallel_fraction=2), lambda d: d.update(repetitions=1)])
def test_schema_rejects_incompatibility(raw, mutation):
    d = raw()
    mutation(d)
    with pytest.raises(DataError):
        load(d)


def test_csv_loading():
    path = ROOT / "docs/validation/phase4/scaling.csv"
    ds = load_bytes(path.read_bytes(), path.name)
    rows = trial_rows(ds)
    assert ds.family == "csv" and ds.warnings
    assert len(rows) == 34 and scaling_points(ds) == []
    assert not compatible(ds, ds)
    out = load_bytes(selection_json(ds, rows[:3]), "selection.json")
    assert len(trial_rows(out)) == 3 and out.family == "csv"


@pytest.mark.parametrize("payload", [b"x,y\n1,2\n", b"schema_version,wall_ns\n1,3\n"])
def test_arbitrary_csv_rejected(payload):
    with pytest.raises(DataError, match="exact Phase 4"):
        load_bytes(payload, "a.csv")


@pytest.mark.parametrize("column,value", [("wall_ns", "nan"), ("warmup", "2"), ("observed_threads", "0"), ("block", "=1+1"), ("strategy", "dijkstra")])
def test_bad_csv_cells(column, value):
    path = ROOT / "docs/validation/phase4/scaling.csv"
    reader = csv.DictReader(io.StringIO(path.read_text()))
    rows = list(reader)
    rows[0][column] = value
    output = io.StringIO()
    writer = csv.DictWriter(output, reader.fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    with pytest.raises(DataError):
        load_bytes(output.getvalue().encode(), "bad.csv")


def test_permission_denied_has_no_numeric_charts(receipt):
    ds = receipt("sequential-smoke", "phase2")
    rows = counter_rows(ds)
    assert rows and all(r["value"] is None for r in rows)
    assert any(r["status"] == "permission_denied" for r in rows)
    assert all(r["scope"] for r in rows)
    from dashboard.charts.cpu import counters
    assert counters(rows, "cpu_cycles") is None
    diagnostic = receipt("diagnostic", "phase2")
    assert counter_rows(diagnostic) == []
    assert counter_rows(receipt()) == []


def test_missing_counters_do_not_become_zero(raw):
    d = raw("sequential-smoke", "phase2")
    for run in d["runs"]:
        run.pop("counters")
        run["derived"]["ipc"] = 10
    ds = load(d)
    assert all(r["value"] is None for r in counter_rows(ds))


def measured_counter(value, raw=None, enabled=100, running=100):
    # Explicit test fixture for transformation contracts; never included in demo receipts.
    return {"status": "available" if enabled == running else "multiplexed", "raw": int(value * running / enabled if raw is None else raw),
            "value": value, "time_enabled_ns": enabled, "time_running_ns": running}


@pytest.mark.parametrize("enabled,running", [(100, 100), (100, 50)])
def test_valid_group_ratios_and_multiplexing(raw, enabled, running):
    d = raw("sequential-smoke", "phase2")
    r = d["runs"][0]
    r["counters"]["cpu_cycles"] = measured_counter(100, enabled=enabled, running=running)
    r["counters"]["instructions"] = measured_counter(250, enabled=enabled, running=running)
    r["derived"].update(ipc=2.5, cpi=0.4)
    rows = counter_rows(load(d))
    assert next(v["value"] for v in rows if v["event"] == "ipc") == 2.5
    assert next(v["value"] for v in rows if v["event"] == "cpi") == 0.4
    count = next(v for v in rows if v["event"] == "cpu_cycles")
    assert count["time_running_ns"] == running and count["raw"] == str(int(100 * running / enabled))


@pytest.mark.parametrize("change", ["zero", "mismatched_times", "inconsistent_ratio", "unavailable"])
def test_invalid_ratios_hidden(raw, change):
    d = raw("sequential-smoke", "phase2")
    r = d["runs"][0]
    r["counters"]["cpu_cycles"] = measured_counter(100)
    r["counters"]["instructions"] = measured_counter(250)
    r["derived"].update(ipc=2.5)
    if change == "zero":
        r["counters"]["cpu_cycles"] = measured_counter(0)
    elif change == "mismatched_times":
        r["counters"]["instructions"] = measured_counter(250, enabled=200, running=200)
    elif change == "inconsistent_ratio":
        r["derived"]["ipc"] = 4
    else:
        r["counters"]["instructions"].update(status="permission_denied", value=None)
    assert next(v["value"] for v in counter_rows(load(d)) if v["event"] == "ipc") is None


def test_unavailable_nonnull_value_rejected(raw):
    d = raw("sequential-smoke", "phase2")
    d["runs"][0]["counters"]["cpu_cycles"]["value"] = 0
    with pytest.raises(DataError):
        load(d)


def test_memory_accounting_labels(receipt):
    ds = receipt("memory", "phase5/receipts")
    rows = memory_rows(ds)
    assert len(rows) == 8 and all("accounting" in r["kind"].lower() for r in rows)
    assert not any("rss" in r["metric"].lower() for r in rows)
    assert ds.raw["process_memory"]["rss_bytes"] > 0
    assert ds.raw["layouts"]["csr"]["physical_memory_bytes"] is None


def test_locality_grouping_and_filters(receipt):
    ds = receipt("cache-study", "phase5/receipts")
    rows = trial_rows(ds)
    assert len(grouped_timings(rows)) == 4
    filtered = filter_rows(rows, active_data_bytes=[4096], repetition=[0])
    assert len(filtered) == 1
    assert filter_rows(rows, pattern=[]) == []
    assert filter_rows(rows, build=["imaginary"]) == []
    assert len(filter_rows(rows, environment=[environment_key(ds)])) == len(rows)
    assert locality_comparable(receipt("locality-sequential", "phase5/receipts"), receipt("locality-random", "phase5/receipts"))


def test_speedup_uses_one_thread_same_algorithm(receipt):
    ds = receipt()
    points = scaling_points(ds)
    base, p2 = sorted(points, key=lambda p: p["requested_threads"])
    assert base["speedup"] == 1 and p2["speedup"] == pytest.approx(base["median_ms"] / p2["median_ms"])
    assert p2["efficiency"] == pytest.approx(p2["speedup"] / 2)
    assert p2["sample_count"] == 15
    assert scaling_points(receipt("parallel-smoke", "phase2")) == []


@pytest.mark.parametrize("mutation", [lambda d: d.update(baseline_definition="Dijkstra time / delta time"),
    lambda d: [r.update(observed_threads=1) for r in d["trials"] if r["requested_threads"] == 2]])
def test_baseline_mismatch_or_observed_team_disables_ratios(raw, mutation):
    d = raw()
    mutation(d)
    ds = load(d)
    assert next(p for p in scaling_points(ds) if p["requested_threads"] == 2)["speedup"] is None


def test_incompatible_datasets_never_pool(receipt, raw):
    a = receipt()
    d = raw()
    for key in ("cpu_model", "build_type", "compiler_flags", "build_revision"):
        b = copy.deepcopy(d)
        b["metadata"][key] = "different"
        assert not compatible(a, load(b))
    b = copy.deepcopy(d)
    b["measurement_scope"] = "different"
    assert not compatible(a, load(b))
    assert compatible(a, load(d))
    b = load(d)
    b.raw["trials"][0]["wall_ns"] += 1
    # Different files retain dataset IDs in grouping; no cross-receipt medians.
    assert len(grouped_timings(trial_rows(a) + trial_rows(receipt("kernels")))) > 2


@pytest.mark.parametrize("fraction,threads,expected", [(0, 8, 1), (1, 8, 8), (0.95, 2, 1 / .525), (.9, 4, 1 / .325)])
def test_amdahl(fraction, threads, expected):
    assert amdahl(fraction, threads) == pytest.approx(expected)


@pytest.mark.parametrize("fraction,threads", [(-.1, 2), (1.1, 2), (math.nan, 2), (.5, 0), (.5, 2.0), (.5, 4097), (True, 2)])
def test_invalid_amdahl(fraction, threads):
    with pytest.raises(DataError):
        amdahl(fraction, threads)


def test_lossless_deterministic_export_and_selection(receipt):
    ds = receipt()
    rows = [r for r in trial_rows(ds) if not r["warmup"]]
    selected = rows[:4]
    assert filtered_csv(selected) == filtered_csv(selected)
    payload = selection_json(ds, selected)
    assert payload == selection_json(ds, selected)
    imported = load_bytes(payload, "selection.json")
    assert imported.raw == ds.raw and trial_rows(imported) == selected
    assert all(p["speedup"] is None for p in scaling_points(imported))
    d = json.loads(payload)
    d["selected_rows"] = ["999999"]
    with pytest.raises(DataError, match="Unknown row"):
        load(d)
    d = json.loads(payload)
    d["source_sha256"] = "wrong"
    with pytest.raises(DataError, match="checksum"):
        load(d)


def test_formula_safe_csv_and_empty_exports():
    data = filtered_csv([{"dataset": "=CMD()", "x": 1, "other": " @SUM(1)"}]).decode()
    assert "'=CMD()" in data and "' @SUM(1)" in data
    assert filtered_csv([]) == b"row_id\n"
    assert grouped_timings([]) == []


def test_no_arbitrary_local_paths():
    with pytest.raises(DataError):
        load_receipt({"path": "/etc/passwd", "sha256": "x"})
    d = catalog()[0].copy()
    d["sha256"] = "wrong"
    with pytest.raises(DataError, match="checksum"):
        load_receipt(d)


def test_genuine_measured_zero_is_preserved(raw):
    d = raw("sequential-smoke", "phase2")
    r = d["runs"][0]
    r["counters"]["cache_misses"] = measured_counter(0)
    rows = counter_rows(load(d))
    assert next(v["value"] for v in rows if v["event"] == "cache_misses") == 0


def test_huge_schedule_is_rejected_before_range_allocation(raw):
    d = raw()
    d["repetitions"] = 10**20
    with pytest.raises(DataError, match="producer bounds"):
        load(d)


def test_invalid_scaled_counter_rejected(raw):
    d = raw("sequential-smoke", "phase2")
    d["runs"][0]["counters"]["instructions"] = measured_counter(250)
    d["runs"][0]["counters"]["instructions"]["value"] = 9
    with pytest.raises(DataError, match="scaled value"):
        load(d)


def test_caller_counters_never_become_openmp_totals(raw):
    d = raw("parallel-smoke", "phase2")
    d["runs"][0]["counters"]["instructions"] = measured_counter(100)
    with pytest.raises(DataError, match="aggregation is unsupported"):
        load(d)


def test_unvalidated_process_scope_rejected(raw):
    d = raw("sequential-smoke", "phase2")
    d["measurement_scope"]["thread_aggregation"] = True
    with pytest.raises(DataError, match="scope"):
        load(d)
