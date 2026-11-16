#!/usr/bin/env python3
"""Meaningful package checks without changing existing implementation tests."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
from results import collect
from verify_evidence import audit


def main():
    academic = ROOT / "docs/academic"
    required = ["README.md", "PROJECT_REPORT.md", "ARCHITECTURE_DIAGRAMS.md", "PRESENTATION.md", "PRESENTATION.pptx",
                "LIVE_DEMO.md", "VIVA_QA.md", "REPRODUCIBILITY.md", "FINAL_EVALUATION.md", "FINAL_VALIDATION.md", "LICENSING.md"]
    assert all((academic / name).is_file() for name in required)
    report = (academic / "PROJECT_REPORT.md").read_text()
    assert re.findall(r"^### (\d+)\.", report, re.M) == [str(i) for i in range(1, 20)]
    viva = (academic / "VIVA_QA.md").read_text()
    assert re.findall(r"^### (\d+)\.", viva, re.M) == [f"{i:02d}" for i in range(1, 61)]
    presentation = (academic / "PRESENTATION.md").read_text()
    assert len(re.findall(r"^## Slide ", presentation, re.M)) == 15
    notes = re.findall(r"### Speaker notes\n\n(.*?)(?=\n## Slide |\Z)", presentation, re.S)
    assert len(notes) == 15 and all(len(n) > 400 for n in notes)
    assert len(re.findall(r"```mermaid\n", (academic / "ARCHITECTURE_DIAGRAMS.md").read_text())) == 7
    links = 0
    for path in [ROOT / "README.md"] + list(academic.glob("*.md")) + [academic / "results/RESULTS.md"]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if re.match(r"[a-zA-Z]+:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            assert (path.parent / target).exists(), f"Broken local link {path}: {target}"
            links += 1
    assert collect() == json.loads((academic / "results/RESULTS.json").read_text()), "Derived results changed"
    verified = audit()
    assert verified == json.loads((ROOT / "docs/validation/phase6/evidence-audit.json").read_text())
    for name in ["archive-locality", "archive-cache-study", "archive-memory", "archive-scaling"]:
        assert (academic / "figures" / (name + ".png")).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        root = ET.parse(academic / "figures" / (name + ".svg")).getroot()
        assert root.tag.endswith("svg")
    ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main", "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
          "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
    with zipfile.ZipFile(academic / "PRESENTATION.pptx") as archive:
        assert archive.testzip() is None
        slides = [n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        assert len(slides) == 15
        for i, expected in enumerate(notes, 1):
            note = ET.fromstring(archive.read(f"ppt/notesSlides/notesSlide{i}.xml"))
            actual = "\n".join(e.text or "" for e in note.findall(".//a:t", ns))
            assert expected.strip() in actual, f"Notes differ on slide {i}"
        charts = sorted(n for n in archive.namelist() if re.fullmatch(r"ppt/charts/chart\d+\.xml", n))
        assert len(charts) == 2
        values = [[float(e.text) for e in ET.fromstring(archive.read(n)).findall(".//c:val/c:numRef/c:numCache/c:pt/c:v", ns)] for n in charts]
        data = collect()
        locality = [r["median_ns"]/1000 for r in data["timings"] if "/phase5/" in r["path"] and "/locality-" in r["path"]]
        scaling = [r["median_ms"] for r in sorted(data["scaling"], key=lambda r:r["requested_threads"])]
        assert values == [locality, scaling], "PPTX chart numbers differ from archived results"
    # Core/receipt hashes before and after script refusal demonstrate no overwrite.
    target = academic / "results/RESULTS.json"
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    refusal = subprocess.run([sys.executable, str(academic / "scripts/results.py"), "--output-dir", str(academic / "results")], capture_output=True)
    assert refusal.returncode != 0 and b"FileExistsError" in refusal.stderr
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before
    with tempfile.TemporaryDirectory(prefix="archgraph-delivery-") as tmp:
        out = Path(tmp) / "new-results"
        subprocess.run([sys.executable, str(academic / "scripts/results.py"), "--output-dir", str(out)], check=True)
        assert json.loads((out / "RESULTS.json").read_text()) == collect()
    print(json.dumps({"report_sections": 19, "viva_answers": 60, "slides": 15, "notes_checked": 15, "mermaid_blocks": 7,
                      "local_link_targets_checked": links, "scientific_figures": 4, "native_chart_data_checked": 2,
                      "receipt_hashes": verified["receipts_checked"], "csv_json_rows": sum(v["rows"] for v in verified["csv_checks"]),
                      "derived_results_repeatable": True, "overwrite_refused": True,
                      "not_verified": ["browser rendering", "presentation-engine rendering", "external link availability at runtime"]}, indent=2))


if __name__ == "__main__":
    main()
