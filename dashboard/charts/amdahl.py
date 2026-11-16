import plotly.graph_objects as go
from dashboard.charts.common import style
from dashboard.data.transform import amdahl


def curve(fraction, maximum, selected, observed=()):
    # Validate all model parameters even when called outside the UI.
    amdahl(fraction, maximum)
    amdahl(fraction, selected)
    if selected > maximum:
        from dashboard.data.validation import DataError
        raise DataError("Selected threads cannot exceed displayed maximum")
    counts = list(range(1, maximum + 1))
    fig = go.Figure(go.Scatter(x=counts, y=[amdahl(fraction, p) for p in counts], mode="lines",
                              name=f"Theoretical · assumed f={fraction:.2f}"))
    fig.add_trace(go.Scatter(x=[selected], y=[amdahl(fraction, selected)], mode="markers", marker_size=12, name="Selected theoretical point"))
    if observed:
        fig.add_trace(go.Scatter(x=[p["requested_threads"] for p in observed], y=[p["speedup"] for p in observed],
                                mode="markers", marker=dict(symbol="diamond", size=12), name="Archived/uploaded observations · delta-stepping"))
    return style(fig, "Amdahl’s Law — theoretical model", "Speedup", "Threads (assumed independent capacity in model)")
