"""Run from the repository: streamlit run dashboard/app.py"""
from pathlib import Path
import sys

# A fixed import root makes both Streamlit CLI and AppTest entrypoints work.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dashboard.data.loader import catalog, load_receipt, load_bytes
from dashboard.data.validation import DataError
from dashboard.data.transform import machine_metadata, environment_key
from dashboard.components.ui import provenance
from dashboard import views

st.set_page_config(page_title="ArchGraph · Performance Observatory", page_icon="◫", layout="wide", initial_sidebar_state="expanded")
st.title("ArchGraph · Performance Observatory")
st.caption("COMPUTER ORGANIZATION & ARCHITECTURE  /  VERIFIED RESULTS, VISIBLE LIMITS")

PAGES = ["CPU overview", "CPU performance", "Memory organization", "Cache & locality", "Multicore performance", "Amdahl’s Law", "Experiment explorer"]
with st.sidebar:
    st.header("ArchGraph / COA")
    page = st.radio("Navigate", PAGES, key="navigation")
    st.divider()
    demo = st.checkbox("Use archived validation receipts", value=True, key="demo")
    st.caption("Demo data are authentic committed measurements, not live runs. Upload output from your local CLI for fresh analysis.")
    uploads = st.file_uploader("Upload result JSON or Phase 4 CSV", type=["json", "csv"], accept_multiple_files=True, key="uploads")

datasets = []
if demo:
    try:
        entries = catalog()
        for entry in entries:
            try:
                datasets.append(load_receipt(entry))
            except (DataError, OSError) as error:
                st.sidebar.warning(f"Receipt unavailable: {entry['path']}: {error}")
    except (OSError, ValueError, KeyError) as error:
        st.warning(f"Archived catalog unavailable: {error}. Upload a supported receipt instead.")
uploads = uploads or []
if len(uploads) > 8 or sum(u.size for u in uploads) > 32 * 1024 * 1024:
    st.error("Upload at most 8 files totaling 32 MiB. Individual files are limited to 16 MiB.")
    uploads = []
for upload in uploads:
    try:
        datasets.append(load_bytes(upload.getvalue(), upload.name))
    except DataError as error:
        st.error(f"Could not import {Path(upload.name).name}: {error}")
# Repeated uploads of identical content do not create accidental extra trials.
datasets = list({(d.digest, tuple(d.selected_rows) if d.selected_rows is not None else None): d for d in datasets}.values())

if not datasets:
    if page == "Amdahl’s Law":
        views.amdahl_view()
    else:
        st.info("No validated measurements loaded. Enable archived receipts or upload a supported result. Amdahl’s Law remains available as a theoretical demonstration.")
else:
    with st.sidebar:
        builds = ["All"] + sorted({machine_metadata(d).get("build_type") or "Unavailable" for d in datasets})
        build = st.selectbox("Build configuration", builds)
        families = ["All"] + sorted({d.raw.get("command", d.raw.get("experiment_type", d.family)) for d in datasets})
        family = st.selectbox("Experiment type", families)
        envs = ["All"] + sorted({environment_key(d) for d in datasets})
        env = st.selectbox("CPU environment record", envs)
    filtered = [d for d in datasets if (build == "All" or (machine_metadata(d).get("build_type") or "Unavailable") == build)
                and (family == "All" or d.raw.get("command", d.raw.get("experiment_type", d.family)) == family)
                and (env == "All" or environment_key(d) == env)]
    if not filtered:
        st.info("No receipts match the metadata filters. Choose All or change the filters.")
        if page == "Amdahl’s Law":
            views.amdahl_view()
    else:
        default = next((i for i, d in enumerate(filtered) if d.raw.get("experiment_type") == "scaling"), 0)
        with st.sidebar:
            idx = st.selectbox("Active receipt", range(len(filtered)), index=default,
                               format_func=lambda i: f"{filtered[i].name} · {filtered[i].digest[:6]}", key="active_receipt")
        ds = filtered[idx]
        provenance(ds)
        st.divider()
        if page == "CPU overview":
            views.overview(ds)
        elif page == "CPU performance":
            views.performance(ds)
        elif page == "Memory organization":
            views.memory_view(ds)
        elif page == "Cache & locality":
            views.locality_view(ds, filtered)
        elif page == "Multicore performance":
            views.multicore(ds)
        elif page == "Amdahl’s Law":
            views.amdahl_view(ds)
        else:
            views.explorer(ds, filtered)
st.divider()
st.caption("ArchGraph-COA · Wall time ≠ cycles · Unknown ≠ zero · Theory ≠ measurement")
