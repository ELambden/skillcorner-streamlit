from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .presentation import event_label

PITCH_LENGTH = 104
PITCH_WIDTH = 68


def pitch_figure(events: pd.DataFrame, title: str = "Dynamic Event Map") -> go.Figure:
    frame = events.copy()
    for column in ["x_start", "y_start", "x_end", "y_end"]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-PITCH_LENGTH / 2, x1=PITCH_LENGTH / 2, y0=-PITCH_WIDTH / 2, y1=PITCH_WIDTH / 2, line={"color": "#f3f2f2", "width": 2})
    fig.add_shape(type="line", x0=0, x1=0, y0=-PITCH_WIDTH / 2, y1=PITCH_WIDTH / 2, line={"color": "#f3f2f2", "width": 1})
    fig.add_shape(type="circle", x0=-9.15, x1=9.15, y0=-9.15, y1=9.15, line={"color": "#f3f2f2", "width": 1})
    if not frame.empty:
        if "event_label" not in frame and "event_type" in frame:
            frame["event_label"] = frame["event_type"].map(event_label)
        color = frame["event_label"] if "event_label" in frame else None
        hover = [column for column in ["player_name", "team_shortname", "event_label", "event_subtype", "time_start", "xthreat"] if column in frame]
        scatter = px.scatter(
            frame,
            x="x_start",
            y="y_start",
            color=color,
            labels={"event_label": "Action type", "x_start": "Pitch length", "y_start": "Pitch width"},
            hover_data=hover,
            opacity=0.72,
        )
        for trace in scatter.data:
            fig.add_trace(trace)
    fig.update_layout(
        title=title,
        paper_bgcolor="#f3f2f2",
        plot_bgcolor="#5d7f67",
        xaxis={"range": [-PITCH_LENGTH / 2 - 3, PITCH_LENGTH / 2 + 3], "showgrid": False, "zeroline": False, "visible": False},
        yaxis={"range": [-PITCH_WIDTH / 2 - 3, PITCH_WIDTH / 2 + 3], "showgrid": False, "zeroline": False, "visible": False, "scaleanchor": "x", "scaleratio": 1},
        height=560,
        margin={"l": 10, "r": 10, "t": 52, "b": 10},
        legend={"orientation": "h", "y": -0.05},
    )
    return fig


def radar_figure(row: pd.Series) -> go.Figure:
    labels = ["Athletic", "Sprint", "Off-ball", "Passing", "Reliability"]
    values = [
        float(row.get("athletic_load_score", 0)),
        float(row.get("sprint_threat_score", 0)),
        float(row.get("off_ball_threat_score", 0)),
        float(row.get("passing_progression_score", 0)),
        float(row.get("reliability_score", 0)),
    ]
    fig = go.Figure(go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill="toself", name=str(row.get("player_short_name", ""))))
    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, 100]}},
        showlegend=False,
        paper_bgcolor="#f3f2f2",
        height=420,
        margin={"l": 30, "r": 30, "t": 30, "b": 30},
    )
    return fig
