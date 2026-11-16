#!/usr/bin/env python3
"""Inventory final academic/evidence files; exclude self-hash and never replace it."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "docs/validation/phase6/DELIVERY_MANIFEST.json"


def files():
    fixed = ["README.md", "docs/ARCHITECTURE.md", "docs/IMPORT_PROVENANCE.md", "docs/ROADMAP.md", "requirements-academic.txt"]
    paths = {ROOT / p for p in fixed}
    for directory in [ROOT / "docs/academic", ROOT / "docs/validation/phase6"]:
        paths.update(p for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p != TARGET)
    return sorted(paths)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    entries = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in files()]
    payload = {"schema_version": 1, "scope": "Final academic package and Phase 6 evidence; manifest excludes its own hash",
               "files": entries}
    if args.check:
        assert json.loads(TARGET.read_text()) == payload, "Package content/inventory changed"
        print(f"Verified {len(entries)} final-delivery file sizes and hashes; manifest self-hash excluded")
    else:
        with TARGET.open("x") as stream:
            stream.write(json.dumps(payload, indent=2) + "\n")
        print(f"Inventoried {len(entries)} final-delivery files")


if __name__ == "__main__":
    main()
