import pandas as pd
import plotly.express as px
from dashboard.charts.common import style


def scaling(points, metric):
    valid = [p for p in points if p.get(metric) is not None]
    if not valid:
        return None
    df = pd.DataFrame(valid)
    df["configuration"] = df["series"] + " · chunk " + df["chunk"].astype(str)
    df = df.sort_values("requested_threads")
    labels = {"median_ms": "Median wall time (ms)", "speedup": "Same-algorithm speedup", "efficiency": "Parallel efficiency"}
    return style(px.line(df, x="requested_threads", y=metric, color="configuration", markers=True,
                         hover_data=["minimum_ms", "maximum_ms", "mad_ms", "sample_count"]),
                 labels[metric], labels[metric], "Requested OpenMP threads")


def individual(rows):
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["configuration"] = df["series"] + " · chunk " + df["chunk"].astype(str)
    return style(px.scatter(df, x="requested_threads", y="wall_ms", color="configuration", symbol="warmup",
                            hover_data=["block", "observed_threads"]), "Individual trials (warmups labeled)", "Wall time (ms)", "Requested threads")
