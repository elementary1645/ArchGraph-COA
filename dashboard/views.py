"""Presentation functions; scientific transformations stay in data/transform.py."""
import streamlit as st
from dashboard.components.ui import facts, plot, table, trial_filters
from dashboard.charts import cpu, memory, locality, scaling, amdahl as amdahl_chart
from dashboard.data.transform import (machine_metadata, trial_rows, counter_rows, memory_rows, scaling_points,
                                     grouped_timings, locality_comparable, amdahl)
from dashboard.data.export import filtered_csv, selection_json


def overview(ds):
    st.header("CPU overview")
    st.write("Read the recorded architecture before interpreting performance.")
    m = machine_metadata(ds)
    d = ds.raw
    t = d.get("topology", m.get("topology", {}))
    diag = d.get("environment_diagnostic", d if ds.family == "diagnostic" else {})
    a, b, c, e = st.columns(4)
    a.metric("Logical processors", t.get("logical_processors", m.get("logical_cpu_hint")) or "Unavailable")
    b.metric("Physical cores in affinity", t.get("physical_cores_in_affinity") or "Unavailable")
    c.metric("SMT detected", "Unavailable" if t.get("smt_detected") is None else ("Yes" if t["smt_detected"] else "No"))
    e.metric("Quota (CPU-time slots)", t.get("quota_cpus") if t.get("quota_cpus") is not None else t.get("quota_status", "Unavailable"))
    facts([("CPU model", m.get("cpu_model")), ("Processor architecture", diag.get("architecture")), ("Operating system", diag.get("os")),
           ("Kernel", diag.get("kernel")), ("Available CPU IDs", t.get("available_cpus")), ("Affinity restricted", t.get("affinity_restricted")),
           ("Physical packages in affinity", t.get("sockets_in_affinity")), ("OpenMP max threads", m.get("openmp_max_threads")),
           ("Compiler", m.get("compiler")), ("Build configuration", m.get("build_type")), ("Compiler flags", m.get("compiler_flags")),
           ("Build revision", m.get("build_revision")), ("Build dirty at configuration", m.get("build_dirty"))])
    cache = d.get("cache_info", {})
    st.subheader("Cache metadata")
    table(cache.get("entries", []))
    st.caption(cache.get("warning", "Cache metadata unavailable in this receipt. Select a Phase 3 result for recorded cache entries."))
    for warning in t.get("limitations", []):
        st.warning(warning)
    st.info("Logical processors are hardware contexts. SMT siblings share core resources; model branding and logical counts do not prove dedicated physical capacity.")


def performance(ds):
    st.header("CPU performance metrics")
    st.write("Hardware PMU observations and elapsed wall time have different scopes.")
    counters = counter_rows(ds)
    numeric = sorted({r["event"] for r in counters if r["value"] is not None})
    if numeric:
        event = st.selectbox("Hardware event or validated same-group ratio", numeric)
        plot(cpu.counters(counters, event), "counter_chart")
    else:
        st.warning("No usable hardware-counter values in this receipt. Missing, permission-denied, unsupported and diagnostic probe values are never replaced with zero.")
    if ds.family == "diagnostic":
        st.info("This is an availability diagnostic, not a graph or memory workload measurement. Probe arithmetic is excluded from workload charts.")
        st.json(ds.raw.get("availability", {}))
    elif ds.family == "multicore":
        st.warning("OpenMP counter aggregation is unsupported. No caller-thread proxy is shown as a team total.")
        st.json(ds.raw.get("counters", {}))
    elif counters:
        st.subheader("Counter status, scope and multiplexing")
        table(counters)
    st.caption("IPC = instructions / cycles; CPI = cycles / instructions. Neither uses wall time. Multiplexed values are scaled estimates; inspect raw counts and enabled/running times.")
    rows = trial_filters(trial_rows(ds), "performance")
    plot(cpu.wall_times(rows), "wall_chart")


def memory_view(ds):
    st.header("Memory organization")
    rows = memory_rows(ds)
    plot(memory.footprint(rows), "memory_chart")
    table(rows)
    rss = ds.raw.get("process_memory", {})
    st.metric("Measured whole-process RSS (bytes)", rss.get("rss_bytes") if rss.get("rss_bytes") is not None else "Unavailable")
    st.caption(rss.get("source", "No process memory snapshot in this receipt."))
    st.info("Representation accounting uses logical sizes, vector capacities and container estimates. These overlapping components are not additive bars. Allocator overhead and per-layout physical memory are unknown. Both layouts coexist in whole-process RSS.")
    if ds.raw.get("command") == "compare-layouts":
        plot(cpu.wall_times(trial_rows(ds)), "layout_times")
        st.caption("Same shortest-path outputs, separate representation implementations. Recorded order is CSR then adjacency; allocation/cache state can confound timing. This is not thread scaling.")


def locality_view(ds, datasets):
    st.header("Cache and locality")
    st.write("Observe access patterns and working sets; keep cache-capacity explanations separate from measurements.")
    if ds.family != "memory" or ds.raw.get("command") not in {"locality", "cache-study"}:
        st.info("Select a locality or cache-study receipt for access-pattern and working-set measurements.")
        return
    candidates = [v for v in datasets if v.digest != ds.digest and locality_comparable(ds, v)]
    extra = st.multiselect("Explicitly compare compatible locality receipts", range(len(candidates)),
                           format_func=lambda i: candidates[i].name, help="Equal recorded environment/build/scope, data/index read count and seed. Traces remain separate; no trials are pooled.")
    rows = trial_rows(ds)
    for i in extra:
        rows += trial_rows(candidates[i])
    rows = trial_filters(rows, "locality")
    plot(locality.locality(rows, ds.raw.get("cache_info", {}).get("entries", [])), "locality_chart")
    if rows:
        table(grouped_timings(rows))
    st.warning("Capacity markers are recorded metadata, not verified L1/L2/L3 timing transitions. Index-stream storage, TLB, prefetching, volatile scalar loads, scheduling and shared-host noise also affect results.")
    st.caption("Spatial locality reuses nearby addresses; temporal locality reuses an active working set. Theoretical expectations do not establish hardware cache hits. Each trace identifies its receipt and configuration.")


def multicore(ds):
    st.header("Multicore performance")
    if ds.family != "multicore":
        st.info("Select a Phase 4 JSON receipt for compatible baseline and environment metadata. Raw CSV is available in Experiment explorer.")
        return
    st.info("Baseline: " + ds.raw["baseline_definition"])
    t = ds.raw.get("topology", {})
    facts([("Logical processors", t.get("logical_processors")), ("Physical cores in affinity", t.get("physical_cores_in_affinity")),
           ("SMT detected", t.get("smt_detected")), ("Available CPU IDs", t.get("available_cpus")), ("Quota CPU-time capacity", t.get("quota_cpus")),
           ("Quota status", t.get("quota_status")), ("Affinity settings", ds.raw.get("affinity"))])
    if t.get("smt_detected"):
        st.warning("SMT siblings share core resources. More threads do not establish scaling across independent physical cores.")
    st.warning("Shared or virtualized hardware and hidden limits may affect these descriptive results. No statistical significance or dedicated-core allocation is established.")
    if ds.raw.get("oversubscribed"):
        st.warning("This experiment explicitly oversubscribed its discovered CPU/quota/runtime ceiling.")
    trials = ds.raw["trials"]
    if any(not r["affinity_restored"] for r in trials):
        st.warning("At least one trial reported failed affinity restoration; inspect the raw flags.")
    if ds.raw.get("affinity", {}).get("requested") == "compact" and any(not r["affinity_applied"] for r in trials):
        st.warning("Compact affinity was requested but not verified for every trial.")
    points = scaling_points(ds)
    metric = st.radio("Scaling metric", ["median_ms", "speedup", "efficiency"], horizontal=True,
                      format_func=lambda v: {"median_ms": "Median time", "speedup": "Speedup", "efficiency": "Efficiency"}[v])
    plot(scaling.scaling(points, metric), "scaling_chart")
    if any(p["speedup"] is None for p in points):
        st.warning("Some ratios are unavailable: baseline definition, selected blocks, timing or observed team size is incompatible. No Dijkstra-to-delta ratio is used.")
    table(points)
    plot(scaling.individual(trial_rows(ds)), "scaling_trials")
    st.caption("Median, minimum, maximum and median absolute deviation are descriptive. Warmups are excluded from medians and labeled separately in individual trials. E(p) = S(p) / requested threads, only when observed teams match.")


def amdahl_view(ds=None):
    st.header("Amdahl’s Law explorer")
    st.info("THEORETICAL MODEL · The parallelizable fraction is assumed, not measured or fitted.")
    a, b, c = st.columns(3)
    fraction = a.slider("Assumed parallelizable fraction", min_value=0.0, max_value=1.0, value=0.95, step=0.01)
    maximum = b.slider("Maximum displayed threads", 2, 256, 32)
    selected = c.number_input("Selected thread count", min_value=1, max_value=maximum, value=min(8, maximum), step=1)
    observed = []
    eligible = ds is not None and ds.family == "multicore" and ds.raw.get("experiment_type") == "scaling"
    if eligible:
        points = scaling_points(ds)
        valid = [p for p in points if p["speedup"] is not None and p["requested_threads"] <= maximum]
        if valid and st.checkbox("Overlay compatible observed delta-stepping speedup", value=False):
            observed = valid
            st.caption("Overlay uses this receipt’s median one-thread delta-stepping baseline, not sequential Dijkstra. Environment limitations still apply.")
    plot(amdahl_chart.curve(fraction, maximum, int(selected), observed), "amdahl_chart")
    st.metric("Theoretical speedup at selected threads", f"{amdahl(fraction, int(selected)):.3f}×")
    st.latex(r"S(p)=\frac{1}{(1-f)+f/p}\qquad E(p)=S(p)/p")
    st.write("A fixed serial fraction limits ideal speedup. Real synchronization, startup, dispatch, memory contention and noise can lower it. The model assumes fixed work and ideal independent parallel capacity.")


def explorer(ds, datasets):
    st.header("Experiment explorer")
    st.write("Inspect individual measurements, provenance and exact source values before exporting a selection.")
    comparison = [v for v in datasets if v.digest != ds.digest]
    if comparison:
        from dashboard.data.transform import compatible
        index = st.selectbox("Check another receipt for pooling compatibility", range(len(comparison)), format_func=lambda i: comparison[i].name)
        if compatible(ds, comparison[index]):
            st.info("Recorded compatibility fields match. Results remain separate; a fingerprint is not proof of the same physical host or controlled conditions.")
        else:
            st.warning("Incompatible or unknown environment, build, workload, baseline or scope. These receipts are not pooled.")
    rows = trial_filters(trial_rows(ds), "explorer")
    table(rows)
    a, b = st.columns(2)
    a.download_button("Download filtered trial CSV", filtered_csv(rows), "archgraph-filtered-trials.csv", "text/csv")
    b.download_button("Download lossless JSON selection", selection_json(ds, rows), "archgraph-selection.json", "application/json")
    st.caption("Filtered CSV is a normalized viewing export, not a Phase 4 producer receipt. JSON selections preserve the original document and exact uint64 integers and can be reimported. Producer summaries remain unchanged; incomplete selections disable scaling ratios.")
    with st.expander("Original producer JSON · unmodified"):
        import json
        st.code(json.dumps(ds.raw, indent=2, ensure_ascii=False, allow_nan=False), language="json")
