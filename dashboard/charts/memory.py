import pandas as pd
import plotly.express as px
from dashboard.charts.common import style


def footprint(rows):
    if not rows:
        return None
    # Separate metric panels avoid stacking overlapping accounting components.
    df = pd.DataFrame(rows)
    df["KiB"] = df["bytes"] / 1024
    fig = px.bar(df, x="metric", y="KiB", color="layout", barmode="group", hover_data=["bytes", "kind"])
    return style(fig, "Representation accounting — overlapping metrics, not additive", "KiB", "Accounting category")
