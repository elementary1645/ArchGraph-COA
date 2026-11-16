"""Deterministic downloads. JSON preserves producer integers and unknown fields."""
import csv
import io
from dashboard.data.loader import canonical
from dashboard.data.schemas import SELECTION_SCHEMA


def selection_json(ds, rows):
    return (canonical({"schema": SELECTION_SCHEMA, "schema_version": 1, "source_sha256": ds.digest,
                       "source_document": ds.raw, "source_family": ds.family, "source_name": ds.name, "selected_rows": [r["row_id"] for r in rows],
                       "note": "Selection only; producer summaries remain original. Dashboard ratios require complete measured blocks."}) + "\n").encode()


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def filtered_csv(rows):
    if not rows:
        return b"row_id\n"
    columns = sorted({key for row in rows for key in row})
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _cell(row.get(key)) for key in columns})
    return text.getvalue().encode("utf-8")
