import pandas as pd
import plotly.express as px
from dashboard.charts.common import style
from dashboard.data.transform import grouped_timings


def locality(rows, caches=()):
    if not rows:
        return None
    points = grouped_timings(rows)
    if not points:
        return None
    df = pd.DataFrame(points)
    df["trace"] = df["dataset"] + " · " + df["series"]
    if df["active_data_bytes"].notna().any():
        fig = px.scatter(df, x="active_data_bytes", y="median_ms", color="trace",
                         hover_data=["data_reads", "index_reads", "stride_elements", "mad_ms", "sample_count"])
        fig.update_xaxes(type="log")
        for c in caches:
            if c.get("type") in {"Data", "Unified"} and c.get("size_bytes") and c.get("level"):
                fig.add_vline(x=c["size_bytes"], line_dash="dot", line_color="#8995AA",
                              annotation_text=f"L{c['level']} reported capacity", annotation_position="top left")
        return style(fig, "Observed locality medians · capacity markers are metadata", "Median wall time (ms)", "Active data working set (bytes, log scale)")
    return style(px.scatter(df, x="trace", y="median_ms", color="trace"), "Observed graph traversal medians", "Median wall time (ms)", "Configuration")
