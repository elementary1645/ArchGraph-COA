"""Bounded structural validation and scientific consistency checks; no coercion."""
import math
import statistics
from dashboard.data.schemas import (EVENTS, MAX_ROWS, MEMORY_COMMANDS, MEMORY_SCHEMA,
                                    MULTICORE_SCHEMA, PATTERNS, STRATEGIES, VALID_COUNTER_STATES)


class DataError(ValueError):
    """An imported document cannot be safely interpreted as a supported receipt."""


def need(condition, message):
    if not condition:
        raise DataError(message)


def obj(value, path):
    need(isinstance(value, dict), f"{path}: expected an object")
    return value


def array(value, path, nonempty=True):
    need(isinstance(value, list) and len(value) <= MAX_ROWS and (value or not nonempty),
         f"{path}: expected {'nonempty ' if nonempty else ''}array, at most {MAX_ROWS} rows")
    return value


def num(value, path, minimum=0, nullable=False, integer=False):
    if nullable and value is None:
        return
    need(type(value) in ((int,) if integer else (int, float)) and math.isfinite(value) and value >= minimum,
         f"{path}: expected {'integer' if integer else 'finite number'} >= {minimum}")


def text(value, path):
    need(isinstance(value, str) and bool(value), f"{path}: expected nonempty text")


def tree(value, depth=0, budget=None):
    budget = [500_000] if budget is None else budget
    budget[0] -= 1
    need(depth <= 32 and budget[0] >= 0, "Document exceeds nesting or structural size limit")
    if isinstance(value, dict):
        for k, v in value.items():
            need(isinstance(k, str), "Object keys must be text")
            tree(v, depth + 1, budget)
    elif isinstance(value, list):
        need(len(value) <= MAX_ROWS, "Array exceeds row limit")
        for v in value:
            tree(v, depth + 1, budget)
    elif isinstance(value, float):
        need(math.isfinite(value), "NaN and infinity are not valid measurements")
    elif isinstance(value, str):
        need(len(value) <= 1_000_000, "Text field exceeds limit")


def counters(values, path):
    for event, c in obj(values, path).items():
        need(event in EVENTS, f"{path}: unknown event {event}")
        obj(c, f"{path}.{event}")
        text(c.get("status"), f"{path}.{event}.status")
        for key in ("value", "raw", "time_enabled_ns", "time_running_ns"):
            num(c.get(key), f"{path}.{event}.{key}", nullable=True, integer=key != "value")
        if c["status"] in VALID_COUNTER_STATES:
            need(c.get("value") is not None, f"{path}.{event}: valid status requires a value")
            enabled, running = c.get("time_enabled_ns"), c.get("time_running_ns")
            need(enabled is not None and running is not None and 0 < running <= enabled,
                 f"{path}.{event}: invalid multiplexing times")
            need(running / enabled >= 0.1, f"{path}.{event}: unreliable running fraction")
            need(c.get("raw") is not None and math.isclose(c["value"], c["raw"] * enabled / running, rel_tol=1e-9, abs_tol=1e-9),
                 f"{path}.{event}: scaled value disagrees with raw/enabled/running")
            need((c["status"] == "available") == (running == enabled), f"{path}.{event}: inconsistent scheduling status")
        else:
            need(c.get("value") is None, f"{path}.{event}: unavailable value must be null")


def timing(value, path):
    obj(value, path)
    runs = array(value.get("runs"), path + ".runs")
    for i, run in enumerate(runs):
        obj(run, f"{path}.runs[{i}]")
        num(run.get("wall_ns"), path + ".wall_ns")
        counters(run.get("counters", {}), path + ".counters")
        obj(run.get("derived", {}), path + ".derived")
        for k, v in run.get("derived", {}).items():
            num(v, path + ".derived." + k, nullable=True)
    num(value.get("median_wall_ns"), path + ".median_wall_ns")
    need(math.isclose(value["median_wall_ns"], statistics.median(r["wall_ns"] for r in runs), rel_tol=1e-9, abs_tol=1e-6),
         f"{path}: median does not match recorded runs")


def metadata(value):
    obj(value, "metadata")
    for key in ("cpu_model", "build_type", "compiler", "compiler_flags", "build_revision", "build_dirty"):
        if key in value and value[key] is not None:
            text(value[key], "metadata." + key)
    t = value.get("topology")
    if t is not None:
        obj(t, "topology")
        for key in ("logical_processors", "physical_cores_in_affinity", "sockets_in_affinity", "quota_cpus"):
            num(t.get(key), "topology." + key, nullable=True)
        for key in ("smt_detected", "affinity_restricted", "affinity_known"):
            if key in t:
                need(t[key] is None or type(t[key]) is bool, f"topology.{key} must be boolean or null")
        if "limitations" in t:
            for warning in array(t["limitations"], "topology.limitations", nonempty=False):
                text(warning, "topology.limitations")
        for cpu in array(t.get("available_cpus", []), "available_cpus", nonempty=False):
            num(cpu, "available_cpus", integer=True)


def validate(d):
    """Return a recognized producer family. Retain all original fields unchanged."""
    tree(d)
    obj(d, "document")
    need(type(d.get("schema_version")) is int and d["schema_version"] == 1, "Only schema_version 1 is supported")
    for key in ("warnings", "environment_limitations"):
        if key in d:
            for warning in array(d[key], key, nonempty=False):
                text(warning, key)
    if "environment_diagnostic" in d:
        obj(d["environment_diagnostic"], "environment_diagnostic")
    schema = d.get("schema")
    if schema in {MEMORY_SCHEMA, MULTICORE_SCHEMA}:
        need(d.get("status") == "completed" and d.get("verified") is True, "Only completed, verified experiments are supported")
        metadata(d.get("metadata"))
        num(d.get("repetitions"), "repetitions", minimum=1, integer=True)
        num(d.get("warmups"), "warmups", integer=True)
        need(d["repetitions"] <= 10000 and d["warmups"] <= 10000, "Trial counts exceed producer bounds")
    if schema == MEMORY_SCHEMA:
        command = d.get("command")
        need(command in MEMORY_COMMANDS, "Unknown memory experiment command")
        need(d.get("measurement_scope") == "calling_thread_user_space_no_inheritance; PMU windows include clock/control overhead",
             "Unsupported memory counter/timing scope")
        cache = obj(d.get("cache_info"), "cache_info")
        for entry in array(cache.get("entries"), "cache_info.entries", nonempty=False):
            obj(entry, "cache entry")
            for key in ("level", "size_bytes", "line_bytes"):
                num(entry.get(key), "cache." + key, nullable=True, integer=True)
        if command in {"memory", "compare-layouts"} or (command == "locality" and "layouts" in d):
            layouts = obj(d.get("layouts"), "layouts")
            for name in ("csr", "adjacency"):
                layout = obj(layouts.get(name), "layouts." + name)
                for key in ("logical_payload_bytes", "used_metadata_bytes", "capacity_storage_bytes", "container_object_bytes", "accounted_total_bytes"):
                    num(layout.get(key), "layouts." + key, integer=True)
                need(layout["accounted_total_bytes"] == layout["capacity_storage_bytes"] + layout["container_object_bytes"], "Inconsistent accounted memory total")
            num(obj(d.get("process_memory"), "process_memory").get("rss_bytes"), "rss_bytes", nullable=True, integer=True)
        if command == "compare-layouts":
            need(d.get("outputs_identical") is True, "Layout comparison must verify equal outputs")
            timing(d.get("csr_dijkstra"), "csr_dijkstra")
            timing(d.get("adjacency_dijkstra"), "adjacency_dijkstra")
        elif command in {"locality", "cache-study"}:
            experiments = d.get("experiments") if command == "cache-study" else [d.get("experiment", d)]
            for e in array(experiments, "experiments"):
                obj(e, "experiment")
                need(e.get("pattern") in PATTERNS, "Unknown locality pattern")
                if e["pattern"] not in {"csr", "adjacency"}:
                    for key in ("allocated_data_bytes", "active_data_bytes", "data_reads", "index_reads", "seed", "stride_elements"):
                        num(e.get(key), "experiment." + key, integer=True)
                    need(0 < e["active_data_bytes"] <= e["allocated_data_bytes"], "Invalid active working set")
                timing(e.get("timing"), "experiment.timing")
        return "memory"
    if schema == MULTICORE_SCHEMA:
        need(d.get("experiment_type") in {"scaling", "parallel-kernels"}, "Unknown multicore experiment type")
        need(d.get("algorithm") == ("delta-stepping" if d["experiment_type"] == "scaling" else "checksum-transform"), "Incompatible multicore algorithm")
        for key in ("baseline_definition", "measurement_scope", "trial_order"):
            text(d.get(key), key)
        for key in ("topology", "runtime", "affinity", "graph_provenance", "amdahl"):
            obj(d.get(key), key)
        metadata({"topology": d["topology"]})
        f = d["amdahl"].get("assumed_parallel_fraction")
        num(f, "parallel fraction")
        need(f <= 1 and d["amdahl"].get("theoretical") is True, "Amdahl assumptions must be explicitly theoretical")
        counters(d.get("counters", {}), "counters")
        trials = array(d.get("trials"), "trials")
        for r in trials:
            obj(r, "trial")
            for key in ("requested_threads", "observed_threads"):
                num(r.get(key), key, minimum=1, integer=True)
                need(r[key] <= 4096, "Thread count exceeds producer bound")
            for key in ("block", "chunk", "checksum"):
                num(r.get(key), key, integer=True)
            need(r["block"] < 10000 and r["chunk"] <= 4096 and r["checksum"] <= 2**64-1, "Trial fields exceed producer bounds")
            num(r.get("wall_ns"), "wall_ns", minimum=1e-300)
            for key in ("warmup", "affinity_applied", "affinity_restored"):
                need(type(r.get(key)) is bool, f"{key} must be boolean")
            need(r.get("strategy") in STRATEGIES, "Unknown trial strategy")
            need((r["strategy"] == "delta-stepping") == (d["experiment_type"] == "scaling"), "Trial strategy does not match experiment")
        summaries = array(d.get("summaries"), "summaries")
        keys = set()
        for s in summaries:
            obj(s, "summary")
            key = (s.get("strategy"), s.get("chunk"), s.get("requested_threads"))
            need(key not in keys, "Duplicate multicore summary")
            keys.add(key)
            matching = [r["wall_ns"] for r in trials if not r["warmup"] and (r["strategy"], r["chunk"], r["requested_threads"]) == key]
            need(bool(matching), "Summary has no measured trials")
            for name in ("median_wall_ns", "minimum_wall_ns", "maximum_wall_ns", "mad_wall_ns"):
                num(s.get(name), name)
            med = statistics.median(matching)
            expected = {"median_wall_ns": med, "minimum_wall_ns": min(matching), "maximum_wall_ns": max(matching),
                        "mad_wall_ns": statistics.median(abs(v - med) for v in matching)}
            need(all(math.isclose(s[name], v, rel_tol=1e-9, abs_tol=1e-6) for name, v in expected.items()), "Summary statistics mismatch")
            for name in ("speedup", "efficiency", "amdahl_speedup"):
                num(s.get(name), name, nullable=True)
        need(keys == {(r["strategy"], r["chunk"], r["requested_threads"]) for r in trials if not r["warmup"]}, "Missing multicore summaries")
        for key in keys:
            measured = [r for r in trials if (r["strategy"], r["chunk"], r["requested_threads"]) == key and not r["warmup"]]
            warmups = [r for r in trials if (r["strategy"], r["chunk"], r["requested_threads"]) == key and r["warmup"]]
            need(len(measured) == d["repetitions"] and len(warmups) == d["warmups"], "Trial counts disagree with repetition/warmup configuration")
            need({r["block"] for r in measured} == set(range(d["repetitions"])) and {r["block"] for r in warmups} == set(range(d["warmups"])), "Duplicate or missing trial blocks")
        return "multicore"
    need(schema is None, "Unknown schema identifier")
    if d.get("status") == "diagnostic":
        metadata(d.get("metadata"))
        counters(d.get("availability", {}), "availability")
        return "diagnostic"
    if "cpu_model" in d and "openmp_max_threads" in d:
        metadata(d)
        return "cpu"
    need(d.get("algorithm") in {"dijkstra", "delta-stepping"} and d.get("status") == "completed" and d.get("verified") is True,
         "Not a supported benchmark, CPU, diagnostic, memory or multicore receipt")
    metadata(d.get("metadata"))
    need(d.get("unit") == "wall_ns", "Benchmark timing unit must be wall_ns")
    timing(d, "benchmark")
    samples = array(d.get("samples"), "samples")
    need(samples == [r["wall_ns"] for r in d["runs"]], "Samples differ from individual runs")
    need(d.get("repetitions") == len(samples), "Repetition count mismatch")
    scope = obj(d.get("measurement_scope"), "measurement_scope")
    need(scope.get("hardware") == "calling_thread_user_space" and scope.get("inherit") is False and scope.get("thread_aggregation") is False,
         "Unsupported benchmark counter scope; worker aggregation is not validated")
    if d["algorithm"] == "delta-stepping":
        need(all(c.get("value") is None for r in d["runs"] for c in r.get("counters", {}).values()),
             "OpenMP hardware aggregation is unsupported, including one-thread delta-stepping")
    return "benchmark"
