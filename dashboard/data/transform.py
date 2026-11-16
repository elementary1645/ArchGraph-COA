"""Pure, unit-testable adapters. Never pool incompatible result documents."""
import hashlib
import math
import statistics
from dashboard.data.loader import canonical
from dashboard.data.schemas import VALID_COUNTER_STATES
from dashboard.data.validation import DataError, need


def machine_metadata(ds):
    if ds.family == "cpu":
        return ds.raw
    return ds.raw.get("metadata", {})


def environment_key(ds):
    if ds.family == "csv":
        return "unknown:" + ds.digest
    m = machine_metadata(ds)
    # Model name alone cannot establish identical host/environment.
    return hashlib.sha256(canonical({"metadata": m, "topology": ds.raw.get("topology", m.get("topology")),
                                    "runtime": ds.raw.get("runtime"), "diagnostic": ds.raw.get("environment_diagnostic", {}).get("kernel")}).encode()).hexdigest()[:12]


def compatibility_key(ds):
    d = ds.raw
    return canonical({"environment": environment_key(ds), "family": ds.family,
                      "algorithm": d.get("algorithm"), "command": d.get("command", d.get("experiment_type")),
                      "scope": d.get("measurement_scope"), "graph": d.get("input_identity", d.get("graph_provenance")),
                      "source": d.get("source"), "delta": d.get("delta"), "workload": d.get("workload"),
                      "size": d.get("size_elements"), "seed": d.get("seed"), "baseline": d.get("baseline_definition")})


def compatible(a, b):
    # Unknown environment is never permission to combine distinct files.
    required = ("cpu_model", "build_type", "compiler", "compiler_flags", "build_revision")
    known = all(all(machine_metadata(ds).get(k) for k in required) for ds in (a, b))
    return known and a.family != "csv" and b.family != "csv" and compatibility_key(a) == compatibility_key(b)


def trial_rows(ds, apply_selection=True):
    d, rows = ds.raw, []
    m = machine_metadata(ds)
    env = environment_key(ds)

    def add(run, series, **context):
        row = {"row_id": str(len(rows)), "dataset": ds.name, "dataset_sha256": ds.digest,
               "environment": env, "build": m.get("build_type") or "Unavailable", "experiment": d.get("command", d.get("experiment_type", ds.family)),
               "series": series, "repetition": run.get("index", len(rows)), "wall_ns": run["wall_ns"],
               "wall_ms": run["wall_ns"] / 1_000_000, "warmup": run.get("warmup", False),
               "requested_threads": run.get("requested_threads", d.get("requested_threads")),
               "observed_threads": run.get("observed_threads", d.get("actual_threads")),
               "block": run.get("block"), "chunk": run.get("chunk"),
               "checksum": str(run["checksum"]) if "checksum" in run else None,
               "pattern": None, "active_data_bytes": None, "allocated_data_bytes": None,
               "data_reads": None, "index_reads": None, "seed": None, "stride_elements": None,
               "affinity_applied": run.get("affinity_applied"), "affinity_restored": run.get("affinity_restored")}
        row.update(context)
        rows.append(row)

    if ds.family in {"multicore", "csv"}:
        for r in d["trials"]:
            add(r, r["strategy"], repetition=r["block"])
    elif ds.family == "benchmark":
        for r in d["runs"]:
            add(r, d["algorithm"])
    elif ds.family == "memory":
        command = d["command"]
        if command == "compare-layouts":
            for layout in ("csr", "adjacency"):
                for i, r in enumerate(d[layout + "_dijkstra"]["runs"]):
                    add(r, layout + " Dijkstra", repetition=i)
        elif command in {"locality", "cache-study"}:
            exps = d["experiments"] if command == "cache-study" else [d.get("experiment", d)]
            for idx, e in enumerate(exps):
                ctx = {k: e.get(k) for k in ("pattern", "active_data_bytes", "allocated_data_bytes", "data_reads", "index_reads", "seed", "stride_elements")}
                for i, r in enumerate(e["timing"]["runs"]):
                    add(r, f"{e['pattern']} · set {idx + 1}", repetition=i, **ctx)
    if apply_selection and ds.selected_rows is not None:
        return [r for r in rows if r["row_id"] in ds.selected_rows]
    return rows


def filter_rows(rows, **filters):
    return [r for r in rows if all(values is None or r.get(key) in values for key, values in filters.items())]


def grouped_timings(rows):
    groups = {}
    # Includes dataset identity and work parameters: distinct receipts/configurations never pool.
    for r in rows:
        if r["warmup"]:
            continue
        key = (r["dataset_sha256"], r["series"], r["requested_threads"], r["chunk"], r["active_data_bytes"],
               r["data_reads"], r["seed"], r["stride_elements"])
        groups.setdefault(key, []).append(r)
    result = []
    for group in groups.values():
        vals = [r["wall_ns"] for r in group]
        med = statistics.median(vals)
        result.append({**group[0], "median_ms": med / 1e6, "minimum_ms": min(vals) / 1e6,
                       "maximum_ms": max(vals) / 1e6, "mad_ms": statistics.median(abs(x - med) for x in vals) / 1e6,
                       "sample_count": len(vals)})
    return result


def scaling_points(ds):
    """Recompute ratios from complete measured blocks, never from arbitrary filtered trials."""
    if ds.family != "multicore":
        return []
    rows = trial_rows(ds)
    points = grouped_timings(rows)
    d = ds.raw
    baseline_ok = (d["experiment_type"] == "scaling" and d["algorithm"] == "delta-stepping"
                   and d["baseline_definition"] == "median one-thread delta-stepping; Dijkstra only correctness oracle")
    if d["experiment_type"] == "parallel-kernels":
        baseline_ok = d["baseline_definition"] == "median one-thread identical strategy/chunk/workload"
    for point in points:
        baseline = next((b for b in points if b["series"] == point["series"] and b["chunk"] == point["chunk"] and b["requested_threads"] == 1), None)
        relevant = [r for r in rows if not r["warmup"] and r["series"] == point["series"] and r["chunk"] == point["chunk"] and r["requested_threads"] in (1, point["requested_threads"])]
        full = all(len([r for r in relevant if r["requested_threads"] == p]) == d["repetitions"] for p in {1, point["requested_threads"]})
        valid = baseline_ok and baseline is not None and full and all(r["observed_threads"] == r["requested_threads"] for r in relevant)
        ratio = baseline["median_ms"] / point["median_ms"] if valid and point["median_ms"] > 0 and baseline["median_ms"] > 0 else None
        point.update(speedup=ratio, efficiency=ratio / point["requested_threads"] if ratio is not None else None,
                     baseline_compatible=valid)
    return points


def amdahl(fraction, threads):
    need(type(fraction) in (int, float) and math.isfinite(fraction) and 0 <= fraction <= 1, "Parallel fraction must be finite in [0,1]")
    need(type(threads) is int and 1 <= threads <= 4096, "Thread count must be an integer in [1,4096]")
    return 1 / ((1 - fraction) + fraction / threads)


def counter_rows(ds):
    """Expose actual records only; diagnostic probes are not workload measurements."""
    if ds.family not in {"benchmark", "memory"}:
        return []
    d = ds.raw
    runs = []
    if ds.family == "benchmark":
        runs = [("benchmark", i, r) for i, r in enumerate(d["runs"])]
    elif d["command"] == "compare-layouts":
        runs = [(layout, i, r) for layout in ("csr", "adjacency") for i, r in enumerate(d[layout + "_dijkstra"]["runs"])]
    elif d["command"] in {"locality", "cache-study"}:
        exps = d.get("experiments", [d.get("experiment", d)])
        runs = [(f"{e['pattern']} · set {j+1}", i, r) for j, e in enumerate(exps) for i, r in enumerate(e["timing"]["runs"])]
    result = []
    selected = set(ds.selected_rows) if ds.selected_rows is not None else None
    for idx, (series, i, r) in enumerate(runs):
        if selected is not None and str(idx) not in selected:
            continue
        for name, c in r.get("counters", {}).items():
            result.append({"series": series, "repetition": i, "event": name, "status": c["status"],
                           "value": c.get("value") if c["status"] in VALID_COUNTER_STATES else None,
                           "raw": str(c["raw"]) if c.get("raw") is not None else None,
                           "time_enabled_ns": c.get("time_enabled_ns"), "time_running_ns": c.get("time_running_ns"),
                           "diagnostic": c.get("diagnostic"), "scope": canonical(d.get("measurement_scope"))})
        # Use only producer-derived same-group ratios after validating operands and times.
        pairs = {"ipc": ("instructions", "cpu_cycles"), "cpi": ("cpu_cycles", "instructions"),
                 "cache_miss_ratio": ("cache_misses", "cache_references"), "branch_miss_ratio": ("branch_misses", "branch_instructions"),
                 "l1d_read_miss_ratio": ("l1d_read_misses", "l1d_read_accesses"), "ll_read_miss_ratio": ("ll_read_misses", "ll_read_accesses"),
                 "dtlb_read_miss_ratio": ("dtlb_read_misses", "dtlb_read_accesses")}
        for name, value in r.get("derived", {}).items():
            pair = pairs.get(name)
            if pair is None:
                continue
            a, b = (r.get("counters", {}).get(v, {}) for v in pair)
            valid = (value is not None and a.get("status") in VALID_COUNTER_STATES and b.get("status") in VALID_COUNTER_STATES
                     and a.get("value") is not None and b.get("value", 0) > 0
                     and a.get("time_enabled_ns") == b.get("time_enabled_ns") and a.get("time_running_ns") == b.get("time_running_ns")
                     and math.isclose(value, a["value"] / b["value"], rel_tol=1e-9, abs_tol=1e-12))
            result.append({"series": series, "repetition": i, "event": name, "status": "derived_valid" if valid else "unavailable_or_inconsistent",
                           "value": value if valid else None, "scope": canonical(d.get("measurement_scope"))})
    return result


def memory_rows(ds):
    result = []
    for layout, m in ds.raw.get("layouts", {}).items():
        for key, label in [("logical_payload_bytes", "Logical edge payload (accounting)"), ("used_metadata_bytes", "Used representation metadata (accounting)"),
                           ("capacity_storage_bytes", "Vector capacity storage (accounting)"), ("accounted_total_bytes", "Accounted footprint (capacity + container estimate)")]:
            if m.get(key) is not None:
                result.append({"layout": layout, "metric": label, "bytes": m[key], "kind": "Representation accounting / estimate"})
    return result


def locality_comparable(a, b):
    """Permit explicit, separately traced pattern/working-set comparisons with equal read work."""
    if a.family != "memory" or b.family != "memory" or environment_key(a) != environment_key(b):
        return False
    ra, rb = trial_rows(a), trial_rows(b)
    if not ra or not rb or any(r["pattern"] in (None, "csr", "adjacency") for r in ra + rb):
        return False
    signatures = lambda rows: {(r["data_reads"], r["index_reads"], r["seed"]) for r in rows}
    return signatures(ra) == signatures(rb) and a.raw.get("measurement_scope") == b.raw.get("measurement_scope")
