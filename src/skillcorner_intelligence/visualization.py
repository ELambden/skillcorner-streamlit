from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .presentation import event_label

PITCH_LENGTH = 104
PITCH_WIDTH = 68
PITCH_BG = "#5d7f67"
PAGE_BG = "#f3f2f2"
LINE_COLOR = "#f3f2f2"
EVENT_COLORS = {
    "In-possession action": "#edbb00",
    "Off-ball movement": "#d6006c",
    "Available passing lane": "#7acbff",
    "Defensive pressure": "#201e1d",
}
SPEED_COLORS = {
    "walking": "#7acbff",
    "jogging": "#7acbff",
    "running": "#edbb00",
    "hsr": "#d6006c",
    "sprinting": "#201e1d",
    "sprint": "#201e1d",
}


def _numeric_coordinates(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    coordinate_columns = [
        "x_start",
        "y_start",
        "x_end",
        "y_end",
        "player_in_possession_x_start",
        "player_in_possession_y_start",
        "player_in_possession_x_end",
        "player_in_possession_y_end",
    ]
    for column in coordinate_columns:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def _ranked_sample(frame: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    if len(frame) <= max_rows:
        return frame
    result = frame.copy()
    for column in ["dangerous", "received", "xthreat", "distance_covered"]:
        if column not in result:
            result[column] = 0
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)
    return result.sort_values(["dangerous", "received", "xthreat", "distance_covered"], ascending=False).head(max_rows)


def _base_pitch(title: str, height: int = 560) -> go.Figure:
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-PITCH_LENGTH / 2, x1=PITCH_LENGTH / 2, y0=-PITCH_WIDTH / 2, y1=PITCH_WIDTH / 2, line={"color": LINE_COLOR, "width": 2})
    fig.add_shape(type="line", x0=0, x1=0, y0=-PITCH_WIDTH / 2, y1=PITCH_WIDTH / 2, line={"color": LINE_COLOR, "width": 1})
    fig.add_shape(type="circle", x0=-9.15, x1=9.15, y0=-9.15, y1=9.15, line={"color": LINE_COLOR, "width": 1})
    fig.update_layout(
        title=title,
        paper_bgcolor=PAGE_BG,
        plot_bgcolor=PITCH_BG,
        xaxis={"range": [-PITCH_LENGTH / 2 - 3, PITCH_LENGTH / 2 + 3], "showgrid": False, "zeroline": False, "visible": False},
        yaxis={"range": [-PITCH_WIDTH / 2 - 3, PITCH_WIDTH / 2 + 3], "showgrid": False, "zeroline": False, "visible": False, "scaleanchor": "x", "scaleratio": 1},
        height=height,
        margin={"l": 10, "r": 10, "t": 52, "b": 10},
        legend={"orientation": "h", "y": -0.05},
    )
    return fig


def pitch_figure(events: pd.DataFrame, title: str = "Dynamic Event Map") -> go.Figure:
    frame = _numeric_coordinates(events)
    fig = _base_pitch(title)
    if not frame.empty:
        if "event_label" not in frame and "event_type" in frame:
            frame["event_label"] = frame["event_type"].map(event_label)
        color = frame["event_label"] if "event_label" in frame else None
        hover = [column for column in ["player_name", "team_shortname", "event_label", "event_subtype", "time_start", "xthreat"] if column in frame]
        scatter = px.scatter(
            frame.dropna(subset=["x_start", "y_start"]),
            x="x_start",
            y="y_start",
            color=color,
            labels={"event_label": "Action type", "x_start": "Pitch length", "y_start": "Pitch width"},
            hover_data=hover,
            opacity=0.68,
        )
        for trace in scatter.data:
            fig.add_trace(trace)
    return fig


def action_flow_figure(events: pd.DataFrame, title: str = "Dynamic Action Flow", max_events: int = 650) -> go.Figure:
    frame = _numeric_coordinates(events).copy()
    if frame.empty:
        return _base_pitch(title)
    if "event_label" not in frame and "event_type" in frame:
        frame["event_label"] = frame["event_type"].map(event_label)
    if "event_label" not in frame:
        frame["event_label"] = "Action"

    frame = _ranked_sample(frame, max_events)
    frame["flow_x_start"] = frame.get("x_start")
    frame["flow_y_start"] = frame.get("y_start")
    frame["flow_x_end"] = frame.get("x_end")
    frame["flow_y_end"] = frame.get("y_end")

    if "event_type" in frame:
        passing = frame["event_type"].eq("passing_option")
        if {"player_in_possession_x_start", "player_in_possession_y_start"} <= set(frame.columns):
            frame.loc[passing, "flow_x_start"] = frame.loc[passing, "player_in_possession_x_start"].fillna(frame.loc[passing, "x_start"])
            frame.loc[passing, "flow_y_start"] = frame.loc[passing, "player_in_possession_y_start"].fillna(frame.loc[passing, "y_start"])
            frame.loc[passing, "flow_x_end"] = frame.loc[passing, "x_start"]
            frame.loc[passing, "flow_y_end"] = frame.loc[passing, "y_start"]

    frame = frame.dropna(subset=["flow_x_start", "flow_y_start"])
    fig = _base_pitch(title)
    if frame.empty:
        return fig

    has_end = frame[["flow_x_end", "flow_y_end"]].notna().all(axis=1)
    for label, group in frame.loc[has_end].groupby("event_label", dropna=False):
        color = EVENT_COLORS.get(str(label), "#0088b0")
        xs: list[float | None] = []
        ys: list[float | None] = []
        for row in group.itertuples(index=False):
            xs.extend([float(row.flow_x_start), float(row.flow_x_end), None])
            ys.extend([float(row.flow_y_start), float(row.flow_y_end), None])
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            line={"color": color, "width": 2},
            opacity=0.62,
            name=str(label),
            hoverinfo="skip",
        ))

    hover_columns = [column for column in ["time_start", "event_label", "player_name", "player_in_possession_name", "team_shortname", "event_subtype", "speed_avg_band", "distance_covered", "xthreat", "dangerous", "received", "targeted", "third_start", "third_end"] if column in frame]
    point_frame = frame.copy()
    point_frame["marker_x"] = point_frame["flow_x_end"].fillna(point_frame["flow_x_start"])
    point_frame["marker_y"] = point_frame["flow_y_end"].fillna(point_frame["flow_y_start"])
    point_frame["marker_size"] = 8 + pd.to_numeric(point_frame.get("dangerous", 0), errors="coerce").fillna(0) * 5 + pd.to_numeric(point_frame.get("xthreat", 0), errors="coerce").fillna(0).clip(lower=0) * 30

    points = px.scatter(
        point_frame,
        x="marker_x",
        y="marker_y",
        color="event_label",
        size="marker_size",
        hover_data=hover_columns,
        opacity=0.84,
        labels={"event_label": "Action type"},
    )
    for trace in points.data:
        trace.marker.line = {"width": 1, "color": "white"}
        fig.add_trace(trace)
    return fig


def offball_run_figure(runs: pd.DataFrame, title: str = "Off-ball Run Map", max_runs: int = 450) -> go.Figure:
    frame = _numeric_coordinates(runs).dropna(subset=["x_start", "y_start", "x_end", "y_end"])
    if len(frame) > max_runs:
        frame = frame.sort_values(["dangerous", "received", "distance_covered"], ascending=False).head(max_runs)
    fig = _base_pitch(title)
    if frame.empty:
        return fig

    if "speed_avg_band" not in frame:
        frame["speed_avg_band"] = "run"
    frame["speed_avg_band"] = frame["speed_avg_band"].fillna("run").astype(str)
    frame["run_label"] = frame["speed_avg_band"].str.replace("_", " ").str.title()

    for speed_band, group in frame.groupby("speed_avg_band", dropna=False):
        color = SPEED_COLORS.get(str(speed_band).lower(), "#0088b0")
        xs: list[float | None] = []
        ys: list[float | None] = []
        for row in group.itertuples(index=False):
            xs.extend([float(row.x_start), float(row.x_end), None])
            ys.extend([float(row.y_start), float(row.y_end), None])
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            line={"color": color, "width": 2},
            opacity=0.72,
            name=str(speed_band).replace("_", " ").title(),
            hoverinfo="skip",
        ))

    hover = [column for column in ["player_name", "team_shortname", "event_subtype", "speed_avg_band", "distance_covered", "targeted", "received", "dangerous", "xthreat"] if column in frame]
    marker_size = 9 + pd.to_numeric(frame.get("dangerous", 0), errors="coerce").fillna(0) * 5
    points = px.scatter(
        frame,
        x="x_end",
        y="y_end",
        color="run_label",
        size=marker_size,
        hover_data=hover,
        opacity=0.86,
        labels={"run_label": "Speed band"},
    )
    for trace in points.data:
        trace.showlegend = False
        fig.add_trace(trace)
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
        paper_bgcolor=PAGE_BG,
        height=420,
        margin={"l": 30, "r": 30, "t": 30, "b": 30},
    )
    return fig
