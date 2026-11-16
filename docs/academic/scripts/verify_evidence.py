#!/usr/bin/env python3
"""Audit existing receipts and historical import hashes without changing them."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from dashboard.data.loader import catalog, load_receipt
from dashboard.data.transform import trial_rows


def audit():
    receipts = []
    for entry in catalog():
        ds = load_receipt(entry)
        receipts.append({"path": entry["path"], "sha256": entry["sha256"], "schema_valid": True,
                         "origin": entry["origin"], "family": ds.family, "trial_rows": len(trial_rows(ds)),
                         "build_revision": ds.raw.get("metadata", ds.raw).get("build_revision")})
    assert len(receipts) == 13, "Expected the audited 13-receipt catalog"
    csv_checks = []
    for name in ("scaling", "kernels"):
        base = ROOT / "docs/validation/phase4"
        raw = json.loads((base / (name + ".json")).read_text())
        with (base / (name + ".csv")).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == len(raw["trials"])
        for row, trial in zip(rows, raw["trials"]):
            for key in ("wall_ns", "checksum", "block", "chunk", "requested_threads", "observed_threads"):
                assert (float(row[key]) if key == "wall_ns" else int(row[key])) == trial[key]
            for key in ("warmup", "affinity_applied", "affinity_restored"):
                assert bool(int(row[key])) == trial[key]
        csv_checks.append({"path": str((base / (name + ".csv")).relative_to(ROOT)), "rows": len(rows), "equal_to_json": True})
    original = json.loads((ROOT / "docs/import-manifest.json").read_text())
    expected_changes = {"src/algorithms/delta_stepping.cpp", "include/dynagraph/algorithms/delta_stepping.hpp"}
    imports = []
    for item in original["files"]:
        path = item["destination_path"]
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        equal = actual == item["upstream_sha256"]
        if item["status"] == "unchanged" and path not in expected_changes:
            assert equal, f"Unexpected change to originally unchanged import: {path}"
        imports.append({"path": path, "initial_import_status": item["status"], "upstream_sha256": item["upstream_sha256"],
                        "current_sha256": actual, "equal_to_upstream": equal,
                        "explanation": "Phase 4 optional observed-team output; algorithm loop preserved" if path in expected_changes else
                                       ("Initial adaptation recorded by original manifest" if item["status"] == "adapted" else "Unchanged imported bytes")})
    return {"schema_version": 1, "receipts_checked": len(receipts), "receipts": receipts, "csv_checks": csv_checks,
            "upstream_source": original["source"], "upstream_commit": original["commit"], "import_files": imports,
            "licensing": "No upstream license grant recorded; redistribution clearance unresolved",
            "scope": "Byte integrity, supported schemas and recorded provenance; not authentication of hardware or a license grant"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="New evidence JSON path; refuses to replace existing evidence")
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
