#!/usr/bin/env python3
"""Build an editable 15-slide PPTX from reviewed Markdown and archived receipt data."""
import argparse
from pathlib import Path
import re
import sys
import zipfile
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
from results import collect

BLUE, INK, LIGHT = "176B87", "182840", "F5F7FB"


def text(slide, value, x, y, w, h, size=24, color=INK, bold=False):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.word_wrap = True
    for i, line in enumerate(value.split("\n")):
        para = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        para.text = line
        para.font.name = "Aptos"
        para.font.size = Pt(size)
        para.font.bold = bold
        para.font.color.rgb = RGBColor.from_string(color)
        para.space_after = Pt(12)
    return shape


def box(slide, value, x, y, w=3.5, h=1.0):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string("E8EDF5")
    shape.line.color.rgb = RGBColor.from_string(BLUE)
    text(slide, value, x + .15, y + .15, w - .3, h - .2, 20)


def chart(slide, categories, values, name, x, y, w, h, unit):
    data = CategoryChartData()
    data.categories = categories
    data.add_series(name, values)
    c = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), data).chart
    c.has_legend = False
    c.value_axis.has_title = True
    c.value_axis.axis_title.text_frame.text = unit
    c.value_axis.minimum_scale = 0
    c.category_axis.tick_labels.font.size = Pt(15)
    c.value_axis.tick_labels.font.size = Pt(14)
    c.series[0].format.fill.solid()
    c.series[0].format.fill.fore_color.rgb = RGBColor.from_string(BLUE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True, help="New PPTX path only")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    source = (ROOT / "docs/academic/PRESENTATION.md").read_text()
    blocks = re.findall(r"## Slide (\d+) — (.*?)\n\n### On slide\n\n(.*?)\n\n### Speaker notes\n\n(.*?)(?=\n## Slide |\Z)", source, re.S)
    assert len(blocks) == 15
    data = collect()
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    prs.core_properties.title = "ArchGraph-COA — Academic Delivery"
    prs.core_properties.author = "ArchGraph-COA project contributors"
    prs.core_properties.subject = "COA methodology; archived measurements and explicitly theoretical models"
    for num, title, content, notes in blocks:
        number = int(num)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(LIGHT)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(.14))
        bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor.from_string(BLUE); bar.line.fill.background()
        text(slide, "ARCHGRAPH / COMPUTER ORGANIZATION & ARCHITECTURE", .6, .32, 12, .4, 13, BLUE, True)
        text(slide, title, .6, .9, 12, .8, 34, INK, True)
        bullets = "\n".join("• " + line[2:] for line in content.splitlines() if line.startswith("- "))
        body_w = 6.0 if number in {5, 6, 7, 8, 11} else 12.0
        text(slide, bullets, .65, 2.0, body_w, 4.5, 25 if body_w > 6 else 22)
        if number == 5:
            for i, label in enumerate(["Seeded input + manifest", "C++ engine + verification", "Receipts + dashboard"]):
                box(slide, label, 7.2, 2.0 + i*1.35, 5.1, 1.0)
                if i < 2: text(slide, "↓", 9.4, 2.95+i*1.35, .5, .5, 22, BLUE)
        elif number == 6:
            for i, label in enumerate(["offsets: 0, 2, 3, 3", "destinations: 1, 2, 2", "weights: 4, 7, 2"]):
                box(slide, label, 7.2, 2.0+i*1.25, 5.1, .95)
            text(slide, "Illustrative CSR values, not benchmark data", 7.2, 6, 5.1, .6, 13)
        elif number == 7:
            for i, label in enumerate(["Fresh paired events + wall clock", "Validate scope, times and results", "Real values or explicit null/status"]):
                box(slide, label, 7.2, 2+i*1.35, 5.1, 1.0)
        elif number == 8:
            rows = [r for r in data["timings"] if "/phase5/" in r["path"] and "/locality-" in r["path"]]
            chart(slide, [Path(r["path"]).stem.replace("locality-", "") for r in rows], [r["median_ns"]/1000 for r in rows], "Archived median", 7.0, 2, 5.7, 4, "Median wall us")
            text(slide, "n=5; fixed-order archived trials, no PMU attribution", 7.1, 6.1, 5.3, .6, 12)
        elif number == 11:
            points = sorted(data["scaling"], key=lambda p:p["requested_threads"])
            chart(slide, [str(p["requested_threads"])+" thread(s)" for p in points], [p["median_ms"] for p in points], "Delta-stepping median", 7, 2, 5.7, 4, "Median wall ms")
            text(slide, "Archived Phase 4; n=15 per count; one visible core + SMT", 7.1, 6.1, 5.3, .6, 12)
        text(slide, f"ARCHIVED ≠ LIVE  ·  THEORY ≠ MEASUREMENT  ·  {number:02d} / 15", .65, 7.0, 12, .3, 11, BLUE)
        slide.notes_slide.notes_text_frame.text = notes.strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(args.output)
    checked = Presentation(args.output)
    assert len(checked.slides) == 15
    assert all(len(s.notes_slide.notes_text_frame.text) > 150 for s in checked.slides)
    for slide in checked.slides:
        for shape in slide.shapes:
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left+shape.width <= checked.slide_width+10 and shape.top+shape.height <= checked.slide_height+10
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        assert len([n for n in archive.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)]) == 15
    print("PPTX: 15 editable slides, 15 notes pages, two native data charts, valid ZIP/reopen and shape bounds")
    print("No PowerPoint/LibreOffice/browser rendering verification was performed")


if __name__ == "__main__":
    main()
