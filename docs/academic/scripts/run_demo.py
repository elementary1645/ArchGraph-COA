#!/usr/bin/env python3
"""Capture a repeatable PMU-independent demo into a NEW directory only."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from dashboard.data.loader import load_bytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="Must not already exist")
    args = parser.parse_args()
    cli = args.cli.resolve(strict=True)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    commands = []

    def capture(name, options, structured=True):
        command = [str(cli)] + [str(v) for v in options]
        result = subprocess.run(command, check=True, capture_output=True)
        path = out / (name + ".json")
        path.write_bytes(result.stdout)
        commands.append({"argv": command, "stdout": path.name, "stderr": result.stderr.decode()})
        parsed = json.loads(result.stdout)
        if structured:
            load_bytes(result.stdout, path.name)
        return parsed

    gen = [sys.executable, "-B", str(ROOT / "benchmarks/python/generate.py"), "generate", "--spec",
           str(ROOT / "benchmarks/configs/chain-v1.json"), "--output", str(out / "graph")]
    subprocess.run(gen, check=True, capture_output=True)
    commands.append({"argv": gen})
    verify = [sys.executable, "-B", str(ROOT / "benchmarks/python/generate.py"), "verify", "--manifest", str(out / "graph/manifest.json")]
    verified = subprocess.run(verify, check=True, capture_output=True)
    (out / "graph-verification.json").write_bytes(verified.stdout)
    commands.append({"argv": verify})
    cpu = capture("cpu", ["--cpu"])
    capture("diagnostic", ["--counter-diagnostics"])
    threads = "1,2" if cpu["topology"]["safe_thread_limit"] >= 2 else "1"
    graph = out / "graph/graph.txt"
    common = ["--input", graph, "--source", "0"]
    sequential = capture("sssp-dijkstra", ["sssp"] + common + ["--algorithm", "dijkstra"], structured=False)
    parallel = capture("sssp-delta", ["sssp"] + common + ["--algorithm", "delta-stepping", "--delta", "16", "--threads", threads.split(",")[-1]], structured=False)
    assert sequential["distances"] == parallel["distances"]
    capture("benchmark", ["bench"] + common + ["--algorithm", "dijkstra", "--repetitions", "5", "--hardware-counters"])
    capture("memory", ["memory", "--input", graph])
    capture("layouts", ["compare-layouts"] + common + ["--runs", "5"])
    for pattern in ("sequential", "random"):
        capture("locality-" + pattern, ["locality", "--pattern", pattern, "--size", "262144", "--accesses", "32768", "--seed", "42", "--runs", "5"])
    capture("cache-study", ["cache-study", "--sizes", "4096,32768,262144", "--accesses", "32768", "--seed", "42", "--runs", "5"])
    scaling = capture("scaling", ["scaling"] + common + ["--threads", threads, "--delta", "16", "--repetitions", "5", "--warmups", "1", "--seed", "42", "--csv", out / "scaling.csv"])
    load_bytes((out / "scaling.csv").read_bytes(), "scaling.csv")
    capture("kernels", ["parallel-kernels", "--threads", threads, "--size", "4096", "--chunks", "16", "--workload", "irregular", "--repetitions", "3", "--warmups", "1", "--seed", "42", "--affinity", "compact"])
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    summary = {"sssp_outputs_equal": True, "thread_list": threads, "scaling_calls": len(scaling["trials"]),
               "purpose": "Tiny correctness/demo capture, not controlled performance evidence",
               "topology": cpu["topology"]}
    (out / "demo-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
