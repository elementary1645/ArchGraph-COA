"""Safe byte imports and a fixed, repository-local receipt catalog."""
from dataclasses import dataclass, field
import csv
import hashlib
import io
import json
from pathlib import Path
from dashboard.data.schemas import CSV_COLUMNS, MAX_BYTES, MAX_ROWS, SELECTION_SCHEMA
from dashboard.data.validation import DataError, need, validate

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Dataset:
    name: str
    family: str
    raw: dict
    digest: str
    origin: str = "Uploaded result — capture time/environment unverified"
    warnings: list[str] = field(default_factory=list)
    selected_rows: list[str] | None = None


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _pairs(pairs):
    d = {}
    for key, value in pairs:
        need(key not in d, f"Duplicate JSON key: {key}")
        d[key] = value
    return d


def _constant(value):
    raise DataError(f"Non-finite JSON constant: {value}")


def _integer(text, column):
    need(text.isascii() and text.isdecimal() and len(text) <= 30, f"CSV {column}: expected unsigned decimal integer")
    return int(text)


def _csv(text):
    reader = csv.DictReader(io.StringIO(text, newline=""))
    need(tuple(reader.fieldnames or ()) == CSV_COLUMNS, "CSV must use the exact Phase 4 raw-trial header; arbitrary CSV tables are unsupported")
    rows = []
    for row in reader:
        need(len(rows) < MAX_ROWS, "CSV row limit exceeded")
        need(None not in row and all(v is not None for v in row.values()), "CSV row has missing or extra columns")
        out = {}
        for key, value in row.items():
            if key == "strategy":
                from dashboard.data.schemas import STRATEGIES
                need(value in STRATEGIES, "CSV strategy is unsupported")
                out[key] = value
            elif key == "wall_ns":
                try:
                    out[key] = float(value)
                except ValueError as e:
                    raise DataError("CSV wall_ns must be numeric") from e
                from dashboard.data.validation import num
                num(out[key], "CSV wall_ns", minimum=1e-300)
            else:
                out[key] = _integer(value, key)
        need(out["schema_version"] == 1 and out["requested_threads"] > 0 and out["observed_threads"] > 0, "Invalid CSV version/thread count")
        need(out["block"] < 10000 and out["chunk"] <= 4096 and out["requested_threads"] <= 4096 and out["observed_threads"] <= 4096 and out["checksum"] <= 2**64-1, "CSV fields exceed producer bounds")
        for key in ("warmup", "affinity_applied", "affinity_restored"):
            need(out[key] in (0, 1), f"CSV {key} must be 0 or 1")
            out[key] = bool(out[key])
        rows.append(out)
    need(bool(rows), "CSV contains no trials")
    return {"schema_version": 1, "trials": rows}


def load_bytes(payload: bytes, name: str, origin=None):
    need(isinstance(payload, bytes) and 0 < len(payload) <= MAX_BYTES, "File must contain 1 byte to 16 MiB")
    try:
        text = payload.decode("utf-8-sig")
        suffix = Path(name).suffix.lower()
        selection = None
        source_name = None
        if suffix == ".csv":
            raw, family = _csv(text), "csv"
        else:
            need(suffix == ".json", "Only .json and Phase 4 .csv files are supported")
            raw = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
            source_family = None
            source_digest = None
            if isinstance(raw, dict) and raw.get("schema") == SELECTION_SCHEMA:
                from dashboard.data.validation import tree
                tree(raw)
                need(raw.get("schema_version") == 1, "Unknown selection version")
                selection = raw.get("selected_rows")
                need(isinstance(selection, list) and len(selection) <= MAX_ROWS and all(isinstance(v, str) for v in selection), "Invalid selected row IDs")
                source_family, source_digest = raw.get("source_family"), raw.get("source_sha256")
                source_name = raw.get("source_name")
                need(isinstance(source_name, str) and bool(source_name), "Selection must name its source")
                raw = raw.get("source_document")
            if source_family == "csv":
                need(isinstance(raw, dict) and raw.get("schema_version") == 1 and isinstance(raw.get("trials"), list), "Invalid CSV selection source")
                stream = io.StringIO()
                writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\n")
                writer.writeheader()
                for row in raw["trials"]:
                    need(isinstance(row, dict) and set(row) == set(CSV_COLUMNS), "Invalid CSV selection row")
                    writer.writerow({k: int(v) if type(v) is bool else v for k, v in row.items()})
                raw, family = _csv(stream.getvalue()), "csv"
            else:
                family = validate(raw)
            if source_digest is not None:
                need(source_digest == hashlib.sha256(canonical(raw).encode()).hexdigest(), "Selection source checksum mismatch")
        digest = hashlib.sha256(canonical(raw).encode()).hexdigest()
        result = Dataset(Path(source_name or name).name[:200], family, raw, digest, selected_rows=selection)
        if origin:
            result.origin = origin
        if family == "csv":
            result.warnings.append("Standalone CSV lacks machine, build, graph, algorithm baseline and measurement scope metadata. Raw inspection only; no speedup or cross-file comparison.")
        if selection is not None:
            from dashboard.data.transform import trial_rows
            need(set(selection) <= {r["row_id"] for r in trial_rows(result, apply_selection=False)}, "Unknown row IDs in selection")
        return result
    except DataError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError, csv.Error) as e:
        raise DataError(f"Malformed or incompatible {Path(name).suffix} input: {str(e)[:180]}") from e


def catalog():
    """Manifest paths are checked under the repository; imported paths are never opened."""
    manifest = json.loads((ROOT / "dashboard/data/receipts.json").read_text())
    return manifest["receipts"]


def load_receipt(entry):
    relative = entry["path"]
    need(relative in {v["path"] for v in catalog()}, "Not an allowlisted receipt")
    path = (ROOT / relative).resolve()
    need(path.is_relative_to(ROOT.resolve()), "Receipt path escapes repository")
    need(path.stat().st_size <= MAX_BYTES, "Receipt exceeds file-size limit")
    payload = path.read_bytes()
    need(hashlib.sha256(payload).hexdigest() == entry["sha256"], "Receipt checksum differs from catalog; audit or upload the changed result explicitly")
    return load_bytes(payload, path.name, entry["origin"])
