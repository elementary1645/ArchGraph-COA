import pandas as pd
import plotly.express as px
from dashboard.charts.common import style


def wall_times(rows):
    if not rows:
        return None
    df = pd.DataFrame(rows)
    return style(px.box(df, x="series", y="wall_ms", color="series", points="all",
                        hover_data=["repetition", "requested_threads", "dataset"]), "Recorded wall-clock trials", "Wall time (ms)", "Configuration")


def counters(rows, event):
    valid = [r for r in rows if r["event"] == event and r["value"] is not None]
    if not valid:
        return None
    return style(px.scatter(pd.DataFrame(valid), x="repetition", y="value", color="series", hover_data=["status"]),
                 f"Recorded {event}", "Ratio" if event in {"ipc", "cpi"} or "ratio" in event else "Count (scaled when multiplexed)", "Repetition")
