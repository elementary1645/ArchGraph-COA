#!/usr/bin/env python3
"""Derive analysis tables from archived receipts; never rewrite source evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from dashboard.data.loader import catalog, load_receipt
from dashboard.data.transform import grouped_timings, machine_metadata, scaling_points, trial_rows


def collect():
    rows, memory, sources = [], [], []
    for entry in catalog():
        ds = load_receipt(entry)
        meta = machine_metadata(ds)
        sources.append({"path": entry["path"], "sha256": entry["sha256"], "origin": entry["origin"],
                        "cpu_model": meta.get("cpu_model"), "build_revision": meta.get("build_revision"),
                        "build_type": meta.get("build_type"), "topology": ds.raw.get("topology", meta.get("topology"))})
        for group in grouped_timings(trial_rows(ds)):
            rows.append({"path": entry["path"], "configuration": group["series"], "threads": group["requested_threads"],
                         "chunk": group["chunk"], "active_data_bytes": group["active_data_bytes"],
                         "data_reads": group["data_reads"], "n": group["sample_count"],
                         "median_ns": group["median_ms"] * 1e6, "min_ns": group["minimum_ms"] * 1e6,
                         "max_ns": group["maximum_ms"] * 1e6, "mad_ns": group["mad_ms"] * 1e6})
        if ds.raw.get("command") == "memory":
            memory.append({"path": entry["path"], "vertices": ds.raw["vertices"], "edges": ds.raw["edges"],
                           "layouts": ds.raw["layouts"], "process_memory": ds.raw["process_memory"]})
        if ds.raw.get("experiment_type") == "scaling":
            scaling = [{k: p[k] for k in ("requested_threads", "median_ms", "minimum_ms", "maximum_ms", "mad_ms", "sample_count", "speedup", "efficiency")}
                       for p in scaling_points(ds)]
    return {"schema_version": 1, "sources": sources, "timings": rows, "memory": memory, "scaling": scaling,
            "limitations": ["Archived descriptive results; distinct environments/configurations are not pooled",
                            "PMU unavailable or unsupported; timings do not establish cache transitions",
                            "One visible physical core with SMT in Phase 4; not independent-core scaling"]}


def render(d):
    lines = ["# Derived archived results", "", "Generated from the 13 checksum-verified catalog receipts; nanoseconds are rounded only for table display.",
             "These are descriptive summaries, not a new benchmark or significance analysis.", "", "| Source | Configuration | Threads | Chunk | Active bytes | n | Median ns | Min ns | Max ns | MAD ns |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in d["timings"]:
        source = Path(r["path"]).name
        lines.append(f"| {source} | {r['configuration']} | {r['threads'] if r['threads'] is not None else 'N/A'} | {r['chunk'] if r['chunk'] is not None else 'N/A'} | {r['active_data_bytes'] if r['active_data_bytes'] is not None else 'N/A'} | {r['n']} | {r['median_ns']:.0f} | {r['min_ns']:.0f} | {r['max_ns']:.0f} | {r['mad_ns']:.0f} |")
    lines += ["", "Source paths, hashes, CPU/build metadata, original memory accounting and independently recomputed scaling ratios are in RESULTS.json.",
              "Phase 2 Dijkstra and delta-stepping entries are different algorithms, not a same-algorithm thread-speedup comparison.",
              "No timing table rows from different source files were pooled.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory only, preserving prior evidence")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    data = collect()
    (args.output_dir / "RESULTS.json").write_text(json.dumps(data, indent=2) + "\n")
    (args.output_dir / "RESULTS.md").write_text(render(data))


if __name__ == "__main__":
    main()
