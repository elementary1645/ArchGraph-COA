#!/usr/bin/env python3
"""Export receipt-derived scientific figures; output files must be new."""
import argparse
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from results import collect


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    targets = [args.output_dir / (name + "." + suffix) for name in
               ("archive-locality", "archive-cache-study", "archive-memory", "archive-scaling") for suffix in ("svg", "png")]
    targets.append(args.output_dir / "sources.json")
    if any(path.exists() for path in targets):
        raise FileExistsError("Refusing to replace an existing figure/source target")
    data = collect()
    plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})

    def save(fig, name):
        fig.tight_layout()
        for suffix in ("svg", "png"):
            path = args.output_dir / f"{name}.{suffix}"
            if path.exists():
                raise FileExistsError(f"Refusing to overwrite figure: {path}")
            fig.savefig(path, dpi=180, metadata={"Creator": "ArchGraph archived receipt analysis"} if suffix == "svg" else None)
            if suffix == "svg":
                path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
        plt.close(fig)

    rows = [r for r in data["timings"] if "/phase5/" in r["path"] and "/locality-" in r["path"]]
    fig, ax = plt.subplots(figsize=(10, 5))
    vals = [r["median_ns"] / 1000 for r in rows]
    ax.bar([Path(r["path"]).stem.replace("locality-", "") for r in rows], vals, color="#176B87")
    ax.errorbar(range(len(rows)), vals, yerr=[[v - r["min_ns"]/1000 for v, r in zip(vals, rows)], [r["max_ns"]/1000-v for v, r in zip(vals, rows)]], fmt="none", ecolor="#26384B", capsize=5)
    ax.set(ylabel="Median wall time (microseconds)", title="Archived locality trials: n=5; whiskers are min/max, not confidence")
    fig.text(.5, .005, "131,072 data/index reads; temporal active set 4 KiB, others 1 MiB; no PMU miss attribution", ha="center", fontsize=10)
    save(fig, "archive-locality")

    rows = [r for r in data["timings"] if r["path"].endswith("/cache-study.json")]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = [r["active_data_bytes"]/1024 for r in rows]
    y = [r["median_ns"]/1000 for r in rows]
    ax.plot(x, y, "o-", color="#176B87")
    ax.set(xscale="log", xlabel="Active data (KiB, logarithmic)", ylabel="Median wall time (microseconds)", title="Archived random working-set study: n=5 per size")
    fig.text(.5, .005, "Fixed 131,072 reads; lines guide the eye, not verified cache boundaries", ha="center", fontsize=10)
    save(fig, "archive-cache-study")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    points = sorted(data["scaling"], key=lambda r:r["requested_threads"])
    axes[0].bar([str(r["requested_threads"]) for r in points], [r["median_ms"] for r in points], color="#176B87")
    axes[0].set(xlabel="Requested / observed threads", ylabel="Median wall time (ms)", title="Archived delta-stepping: n=15")
    pvals = list(range(1, 9))
    axes[1].plot(pvals, [1/(.05+.95/p) for p in pvals], color="#E39138", label="Theoretical, assumed f=0.95")
    axes[1].scatter([r["requested_threads"] for r in points], [r["speedup"] for r in points], color="#176B87", marker="D", label="Observed same-algorithm ratios")
    axes[1].set(xlabel="Threads", ylabel="Speedup", title="Theory is not a fitted measurement")
    axes[1].legend(fontsize=9)
    fig.text(.5, .005, "One-thread delta baseline; shared host with one visible physical core and two SMT contexts", ha="center", fontsize=10)
    save(fig, "archive-scaling")

    m = data["memory"][0]["layouts"]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(["CSR", "Adjacency list"], [m["csr"]["accounted_total_bytes"], m["adjacency"]["accounted_total_bytes"]], color=["#176B87", "#E39138"])
    ax.set(ylabel="Accounted bytes (capacity + container)", title="Archived eight-vertex chain representation accounting")
    fig.text(.5, .005, "56-byte edge payload in each layout; allocator overhead unknown; not measured per-layout RSS", ha="center", fontsize=9)
    save(fig, "archive-memory")
    (args.output_dir / "sources.json").write_text(json.dumps({"source_receipts": data["sources"], "note": "No new performance measurements; plots derive from original receipts"}, indent=2)+"\n")


if __name__ == "__main__":
    main()
