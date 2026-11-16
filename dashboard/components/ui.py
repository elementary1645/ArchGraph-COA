import streamlit as st
import pandas as pd
from dashboard.data.transform import machine_metadata, environment_key


def plot(fig, key=None):
    if fig is None:
        st.info("No compatible numerical measurements for this view.")
    else:
        st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False})


def table(rows):
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("No rows match this selection.")


def facts(items):
    table([{"Field": name, "Recorded value": "Unavailable" if value is None else str(value)} for name, value in items])


def provenance(ds):
    st.caption(ds.origin)
    st.subheader(ds.name)
    m = machine_metadata(ds)
    a, b, c = st.columns(3)
    a.metric("Build", m.get("build_type") or "Unavailable")
    b.metric("Environment record", environment_key(ds))
    c.metric("Source schema", f"{ds.family} · v1")
    st.caption(f"Canonical document SHA-256: {ds.digest}")
    for warning in ds.warnings + ds.raw.get("warnings", []) + ds.raw.get("environment_limitations", []):
        st.warning(str(warning))
    with st.expander("Provenance and measurement boundaries"):
        st.json({"metadata": m, "scope": ds.raw.get("measurement_scope"), "graph": ds.raw.get("graph_provenance", ds.raw.get("input_identity")),
                 "runtime": ds.raw.get("runtime"), "affinity": ds.raw.get("affinity"), "baseline": ds.raw.get("baseline_definition")})


def trial_filters(rows, prefix):
    if not rows:
        return []
    patterns = sorted({r["pattern"] for r in rows if r.get("pattern") is not None})
    sizes = sorted({r["active_data_bytes"] for r in rows if r.get("active_data_bytes") is not None})
    a, b, c = st.columns(3)
    selected_patterns = a.multiselect("Access pattern", patterns, default=patterns, key=prefix + "pattern") if patterns else None
    selected_sizes = b.multiselect("Working set (bytes)", sizes, default=sizes, key=prefix + "size") if sizes else None
    reps = sorted({r["repetition"] for r in rows})
    selected_rep = c.selectbox("Repetition", ["All"] + reps, key=prefix + "rep")
    warmups = st.checkbox("Include warmup trials", value=False, key=prefix + "warmup")
    from dashboard.data.transform import filter_rows
    filtered = filter_rows(rows, pattern=selected_patterns, active_data_bytes=selected_sizes,
                           repetition=None if selected_rep == "All" else [selected_rep])
    return [r for r in filtered if warmups or not r["warmup"]]
