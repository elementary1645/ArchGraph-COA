COLORS = ["#176B87", "#E39138", "#7950A3", "#299885", "#C24C5A", "#526C96"]


def style(fig, title=None, y=None, x=None):
    fig.update_layout(template="plotly_white", font=dict(family="Arial, sans-serif", size=17, color="#182840"),
                      title=title, colorway=COLORS, margin=dict(l=20, r=20, t=55, b=30), height=430,
                      legend=dict(orientation="h", y=-0.25), hovermode="closest")
    if y:
        fig.update_yaxes(title=y, rangemode="tozero")
    if x:
        fig.update_xaxes(title=x)
    return fig
