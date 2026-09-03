from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skillcorner_intelligence.paths import (
    ANALYSIS_JSON,
    EVENT_SAMPLE_CSV,
    MATCH_SUMMARY_CSV,
    MATCH_TEAM_SUMMARY_CSV,
    OFFBALL_RUNS_CSV,
    PHASE_TIMELINE_CSV,
    PLAYER_PROFILES_CSV,
    TEAM_SUMMARY_CSV,
)
from skillcorner_intelligence.presentation import (
    ARCHETYPE_DEFINITIONS,
    SCORE_LABELS,
    defensive_phase_label,
    event_label,
    metric_label,
    phase_label,
    run_subtype_label,
    speed_band_label,
    tracking_label,
)
from skillcorner_intelligence.visualization import match_activity_figure, radar_figure

st.set_page_config(page_title="SkillCorner Football Intelligence Lab", layout="wide")

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Source Serif 4', Georgia, serif; }
.main { background: #f3f2f2; color: #201e1d; }
.block-container { max-width: 1480px; padding-top: 1rem; }
h1, h2, h3 { letter-spacing: 0; color: #201e1d; }
div[data-testid="stMetric"] { border-top: 2px solid #201e1d; padding-top: .45rem; }
.note { color: rgba(32,30,29,.68); font-size: 14px; }
.archetype-panel { border-top: 2px solid #201e1d; padding-top: 10px; margin-top: 8px; }
.archetype-panel strong { display: block; font-size: 18px; margin-bottom: 4px; }
.archetype-panel ul { margin-top: 8px; padding-left: 20px; }
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)

SCORE_COLUMNS = [
    "profile_score",
    "athletic_load_score",
    "sprint_threat_score",
    "off_ball_threat_score",
    "passing_progression_score",
    "reliability_score",
]

ZSCORE_COLUMNS = [
    "profile_z_score",
    "intensity_z_score",
    "volume_z_score",
    "explosiveness_z_score",
    "movement_z_score",
    "progression_z_score",
]

PHYSICAL_FILTER_COLUMNS = [
    "intensity_z_score",
    "volume_z_score",
    "explosiveness_z_score",
]

PROFILE_SCATTER_COLUMNS = [
    *ZSCORE_COLUMNS,
    *SCORE_COLUMNS,
    "minutes",
    "psv99",
    "total_metersperminute_full_all",
    "running_distance_full_all",
    "hsr_distance_full_all",
    "hsr_count_full_all",
    "sprint_distance_full_all",
    "sprint_count_full_all",
    "hi_count_full_all",
    "offballrun_count_p30tip",
    "offballrun_count_dangerous_p30tip",
    "offballrun_count_penaltyarea_p30tip",
    "offballrun_count_targeted_p30tip",
    "offballrun_count_received_p30tip",
    "offballrun_count_shotwithin10s_p30tip",
    "pass_count_linebreak_completed_p30tip",
    "pass_count_torun_completed_p30tip",
    "pass_count_dangerous_completed_p30tip",
    "pass_count_difficultpass_attempted_p30tip",
    "pass_avgxpass_attempted",
    "pass_count_shotwithin10s_p30tip",
    "pass_pct_completed",
]

PLAYER_TABLE_COLUMNS = [
    "player_name",
    "team_name",
    "teams_played",
    "position_group",
    "position_groups",
    "minutes",
    "count_match",
    "profile_context_count",
    "archetype",
    "profile_score",
    "athletic_load_score",
    "sprint_threat_score",
    "off_ball_threat_score",
    "passing_progression_score",
    "profile_z_score",
    "intensity_z_score",
    "volume_z_score",
    "explosiveness_z_score",
    "movement_z_score",
    "progression_z_score",
    "psv99",
    "total_metersperminute_full_all",
    "pass_pct_completed",
]

MATCH_TEAM_COLUMNS = [
    "team_name",
    "events",
    "player_possessions",
    "off_ball_runs",
    "high_intensity_runs",
    "received_runs",
    "targeted_runs",
    "dangerous_events",
    "xthreat_total",
    "longest_run_meters",
    "longest_run_player",
    "top_xthreat_player",
]

COLUMN_CONFIG = {
    "player_name": st.column_config.TextColumn("Player"),
    "player_short_name": st.column_config.TextColumn("Short name"),
    "team_name": st.column_config.TextColumn("Primary club"),
    "teams_played": st.column_config.TextColumn("Clubs in sample"),
    "position_group": st.column_config.TextColumn("Primary role"),
    "position_groups": st.column_config.TextColumn("Roles in sample"),
    "minutes": st.column_config.NumberColumn("Evidence minutes", format="%.0f"),
    "count_match": st.column_config.NumberColumn("Appearances", format="%d"),
    "profile_context_count": st.column_config.NumberColumn("Contexts", format="%d"),
    "archetype": st.column_config.TextColumn("Archetype"),
    "profile_score": st.column_config.ProgressColumn("Overall profile", min_value=0, max_value=100, format="%.1f"),
    "athletic_load_score": st.column_config.ProgressColumn("Athletic load", min_value=0, max_value=100, format="%.1f"),
    "sprint_threat_score": st.column_config.ProgressColumn("Sprint threat", min_value=0, max_value=100, format="%.1f"),
    "off_ball_threat_score": st.column_config.ProgressColumn("Off-ball threat", min_value=0, max_value=100, format="%.1f"),
    "passing_progression_score": st.column_config.ProgressColumn("Passing progression", min_value=0, max_value=100, format="%.1f"),
    "psv99": st.column_config.NumberColumn("Peak speed", format="%.1f"),
    "total_metersperminute_full_all": st.column_config.NumberColumn("Metres per minute", format="%.1f"),
    "pass_pct_completed": st.column_config.NumberColumn("Pass completion", format="%.1f%%"),
    "similarity_gap": st.column_config.NumberColumn("Profile difference", format="%.1f"),
    "profile_z_score": st.column_config.NumberColumn("Profile z", format="%.2f"),
    "intensity_z_score": st.column_config.NumberColumn("Intensity z", format="%.2f"),
    "volume_z_score": st.column_config.NumberColumn("Volume z", format="%.2f"),
    "explosiveness_z_score": st.column_config.NumberColumn("Explosive z", format="%.2f"),
    "movement_z_score": st.column_config.NumberColumn("Movement z", format="%.2f"),
    "progression_z_score": st.column_config.NumberColumn("Progression z", format="%.2f"),
    "events": st.column_config.NumberColumn("Actions", format="%d"),
    "player_possessions": st.column_config.NumberColumn("Possessions", format="%d"),
    "off_ball_runs": st.column_config.NumberColumn("Off-ball runs", format="%d"),
    "high_intensity_runs": st.column_config.NumberColumn("HI runs", format="%d"),
    "received_runs": st.column_config.NumberColumn("Received", format="%d"),
    "targeted_runs": st.column_config.NumberColumn("Targeted", format="%d"),
    "dangerous_events": st.column_config.NumberColumn("Dangerous", format="%d"),
    "xthreat_total": st.column_config.NumberColumn("Threat value", format="%.2f"),
    "distance_covered": st.column_config.NumberColumn("Run distance", format="%.1f m"),
    "speed_avg": st.column_config.NumberColumn("Avg speed", format="%.1f km/h"),
    "xthreat": st.column_config.NumberColumn("xThreat", format="%.3f"),
}


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Missing {path}. Run `python scripts/refresh_all.py`.")
        st.stop()
    frame = pd.read_csv(path)
    text_columns = {
        "player_name", "player_short_name", "player_birthdate", "team_name", "teams_played",
        "position_group", "position_groups", "archetype", "phase_type", "phase_label", "match_label",
        "event_type", "event_label", "event_subtype", "run_type_label", "speed_avg_band", "speed_band_label",
        "time_start", "time_end", "team_shortname", "team_in_possession_shortname", "channel_start",
        "channel_end", "third_start", "third_end", "trajectory_direction", "pass_outcome", "pass_range",
        "team_in_possession_phase_type", "team_out_of_possession_phase_type", "defensive_shape_label",
        "tracking_status", "tracking_label", "longest_run_player", "top_xthreat_player",
    }
    for column in frame.columns:
        if column not in text_columns:
            converted = pd.to_numeric(frame[column], errors="coerce")
            if converted.notna().any():
                frame[column] = converted
    return frame


@st.cache_data(show_spinner=False)
def load_summary() -> dict[str, Any]:
    if not ANALYSIS_JSON.exists():
        return {}
    return json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))


def prepare_display_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    players = load_csv(PLAYER_PROFILES_CSV).copy()
    teams = load_csv(TEAM_SUMMARY_CSV).copy()
    matches = load_csv(MATCH_SUMMARY_CSV).copy()
    events = load_csv(EVENT_SAMPLE_CSV).copy()
    offball_runs = load_csv(OFFBALL_RUNS_CSV).copy()
    match_teams = load_csv(MATCH_TEAM_SUMMARY_CSV).copy()
    phases = load_csv(PHASE_TIMELINE_CSV).copy()
    summary = load_summary()

    teams["phase_label"] = teams["phase_type"].map(phase_label)
    events["event_label"] = events["event_type"].map(event_label)
    if "event_subtype" in events:
        events["action_detail"] = events["event_subtype"].fillna("").map(lambda value: str(value).replace("_", " ").title() if value else "")
    offball_runs["run_type_label"] = offball_runs["event_subtype"].map(run_subtype_label)
    offball_runs["speed_band_label"] = offball_runs["speed_avg_band"].map(speed_band_label)
    offball_runs["phase_label"] = offball_runs["team_in_possession_phase_type"].map(phase_label)
    offball_runs["defensive_shape_label"] = offball_runs["team_out_of_possession_phase_type"].map(defensive_phase_label)
    phases["phase_label"] = phases["team_in_possession_phase_type"].map(phase_label)
    phases["defensive_shape_label"] = phases["team_out_of_possession_phase_type"].map(defensive_phase_label)
    matches["tracking_label"] = matches["tracking_status"].map(tracking_label)
    players["profile_key"] = players["player_id"].astype(str) + " | " + players["player_name"].astype(str) + " | " + players["team_name"].astype(str)
    return players, teams, matches, events, offball_runs, match_teams, phases, summary


def archetype_guide_frame() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Archetype": name,
            "Plain-English meaning": item["short"],
            "Prioritised evidence": "; ".join(item["prioritised"]),
            "Classification signal": item["rule"],
            "Tactical read": item["tactical_use"],
        }
        for name, item in ARCHETYPE_DEFINITIONS.items()
    ])


def render_archetype_panel(name: str) -> None:
    item = ARCHETYPE_DEFINITIONS.get(name)
    if not item:
        return
    st.markdown(
        "<div class='archetype-panel'>"
        f"<strong>{name}</strong>"
        f"<p>{item['meaning']}</p>"
        f"<p><b>Classification signal:</b> {item['rule']}</p>"
        f"<p><b>Tactical read:</b> {item['tactical_use']}</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("Prioritised evidence:")
    for signal in item["prioritised"]:
        st.markdown(f"- {signal}")


def selected_phase_from_label(labels: list[str], selected: str, raw_values: pd.Series) -> str:
    lookup = {phase_label(value): value for value in raw_values.dropna().astype(str).unique()}
    return str(lookup.get(selected, selected))


def options_from_labels(frame: pd.DataFrame, label_column: str, value_column: str) -> dict[str, str]:
    if frame.empty or label_column not in frame or value_column not in frame:
        return {}
    pairs = frame[[label_column, value_column]].dropna().drop_duplicates().sort_values(label_column)
    return dict(zip(pairs[label_column].astype(str), pairs[value_column].astype(str), strict=False))


def zscore_long_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available = [column for column in columns if column in frame]
    if not available:
        return pd.DataFrame(columns=["Score", "Z-score"])
    long = frame[available].mean().reset_index()
    long.columns = ["Score", "Z-score"]
    long["Score"] = long["Score"].map(lambda value: SCORE_LABELS.get(value, value))
    return long


def scatter_metric_options(frame: pd.DataFrame) -> dict[str, str]:
    options: dict[str, str] = {}
    for column in PROFILE_SCATTER_COLUMNS:
        if column in frame and pd.to_numeric(frame[column], errors="coerce").notna().any():
            options[metric_label(column)] = column
    return options


def default_metric_index(options: dict[str, str], column: str) -> int:
    values = list(options.values())
    return values.index(column) if column in values else 0


def selected_dataframe_rows(selection: Any, frame: pd.DataFrame) -> pd.DataFrame:
    selected_rows: list[int] = []
    selection_state = getattr(selection, "selection", None)
    if isinstance(selection_state, dict):
        selected_rows = selection_state.get("rows", [])
    elif selection_state is not None:
        selected_rows = getattr(selection_state, "rows", []) or []
    elif isinstance(selection, dict):
        selected_rows = selection.get("selection", {}).get("rows", [])

    valid_rows = [int(row) for row in selected_rows if 0 <= int(row) < len(frame)]
    if not valid_rows:
        return pd.DataFrame(columns=frame.columns)
    return frame.iloc[valid_rows].copy()


def team_totals_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "events",
        "player_possessions",
        "off_ball_runs",
        "passing_options",
        "on_ball_engagements",
        "dangerous_events",
        "received_runs",
        "targeted_runs",
        "high_intensity_runs",
        "xthreat_total",
    ]
    available = [column for column in numeric_columns if column in frame]
    if frame.empty or not available:
        return pd.DataFrame()
    totals = frame.groupby(["team_id", "team_name"], as_index=False)[available].sum()
    totals["runs_per_possession"] = (totals["off_ball_runs"] / totals["player_possessions"].replace(0, pd.NA)).fillna(0).round(3)
    totals["threat_per_action"] = (totals["xthreat_total"] / totals["events"].replace(0, pd.NA)).fillna(0).round(4)
    return totals


players, teams, matches, events, offball_runs, match_teams, phases, summary = prepare_display_data()

st.title("SkillCorner Football Intelligence Lab")
st.caption("A-League 2024/2025 open-data analysis across physical output, attacking movement, passing, tactical phases and match actions.")

with st.sidebar:
    st.header("Filters")
    positions = ["All", *sorted(players["position_group"].dropna().astype(str).unique())]
    team_options = ["All", *sorted(players["team_name"].dropna().astype(str).unique())]
    position = st.selectbox("Primary role", positions)
    team = st.selectbox("Primary club", team_options)
    max_minutes = int(max(players["minutes"].max(), 1))
    min_minutes = st.slider("Minimum evidence minutes", 0, max_minutes, min(300, max_minutes), 60)
    min_profile = st.slider("Minimum overall profile", 0, 100, 0, 5)
    st.subheader("Physical z-score filters")
    min_intensity_z = st.slider("Minimum intensity z", -3.0, 3.0, -3.0, 0.25)
    min_volume_z = st.slider("Minimum volume z", -3.0, 3.0, -3.0, 0.25)
    min_explosive_z = st.slider("Minimum explosiveness z", -3.0, 3.0, -3.0, 0.25)

filtered = players.copy()
if position != "All":
    filtered = filtered.loc[filtered["position_group"] == position]
if team != "All":
    filtered = filtered.loc[filtered["team_name"] == team]
filtered = filtered.loc[
    (filtered["minutes"] >= min_minutes)
    & (filtered["profile_score"] >= min_profile)
    & (filtered["intensity_z_score"] >= min_intensity_z)
    & (filtered["volume_z_score"] >= min_volume_z)
    & (filtered["explosiveness_z_score"] >= min_explosive_z)
]

tab_overview, tab_players, tab_teams, tab_archetypes, tab_matches, tab_notes = st.tabs([
    "Overview",
    "Players",
    "Teams",
    "Archetypes",
    "Matches",
    "Method Notes",
])

with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Players", f"{players['player_id'].nunique():,}")
    c2.metric("Clubs", f"{players['team_id'].nunique():,}")
    c3.metric("Matches", f"{len(matches):,}")
    c4.metric("Dynamic actions", f"{len(events):,}")

    left, right = st.columns([1.15, 1])
    with left:
        top = filtered.nlargest(20, "profile_score")
        fig = px.bar(
            top.sort_values("profile_score"),
            x="profile_score",
            y="player_short_name",
            color="archetype",
            orientation="h",
            hover_data={"player_name": True, "team_name": True, "position_group": True, "minutes": ":.0f", "profile_score": ":.1f", "player_short_name": False},
            labels={"profile_score": "Overall profile", "player_short_name": "Player", "archetype": "Archetype"},
            title="Top consolidated player profiles in the current filter",
        )
        fig.update_layout(height=620, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Overall profile")
        st.plotly_chart(fig, width="stretch", key="overview_top_profiles_chart")
    with right:
        if filtered.empty:
            st.info("No players match the current filters.")
        else:
            z_view = filtered.copy()
            axis_options = scatter_metric_options(z_view)
            axis_cols = st.columns(2)
            with axis_cols[0]:
                overview_x_label = st.selectbox("X-axis", list(axis_options), index=default_metric_index(axis_options, "volume_z_score"), key="overview_x_axis")
            with axis_cols[1]:
                overview_y_label = st.selectbox("Y-axis", list(axis_options), index=default_metric_index(axis_options, "intensity_z_score"), key="overview_y_axis")
            overview_x = axis_options[overview_x_label]
            overview_y = axis_options[overview_y_label]
            z_view["explosive_size"] = (pd.to_numeric(z_view["explosiveness_z_score"], errors="coerce").fillna(0) + 3.2).clip(lower=0.2)
            fig = px.scatter(
                z_view,
                x=overview_x,
                y=overview_y,
                size="explosive_size",
                color="archetype",
                hover_name="player_name",
                hover_data={
                    "team_name": True,
                    "position_group": True,
                    "profile_z_score": ":.2f",
                    "explosiveness_z_score": ":.2f",
                    "explosive_size": False,
                },
                title=f"{metric_label(overview_x)} vs {metric_label(overview_y)}",
                labels={overview_x: metric_label(overview_x), overview_y: metric_label(overview_y), "archetype": "Archetype"},
            )
            if overview_y.endswith("_z_score") or overview_y.endswith("_z"):
                fig.add_hline(y=0, line_dash="dot", line_color="#201e1d")
            if overview_x.endswith("_z_score") or overview_x.endswith("_z"):
                fig.add_vline(x=0, line_dash="dot", line_color="#201e1d")
            fig.update_layout(height=620, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2")
            st.plotly_chart(fig, width="stretch", key="overview_physical_z_map")

with tab_players:
    search = st.text_input("Search player, club, role or archetype", "")
    table = filtered.copy()
    if search:
        mask = (
            table["player_name"].astype(str).str.contains(search, case=False, na=False)
            | table["teams_played"].astype(str).str.contains(search, case=False, na=False)
            | table["position_groups"].astype(str).str.contains(search, case=False, na=False)
            | table["archetype"].astype(str).str.contains(search, case=False, na=False)
        )
        table = table.loc[mask]

    st.dataframe(
        table[[column for column in PLAYER_TABLE_COLUMNS if column in table]].sort_values("profile_z_score", ascending=False),
        width="stretch",
        hide_index=True,
        column_config=COLUMN_CONFIG,
    )

    if not table.empty:
        st.subheader("Player Z-Score Profile")
        player_labels = table["profile_key"].tolist()
        selected_label = st.selectbox("Inspect player profile", player_labels, key="player_tab_inspect")
        selected_id = pd.to_numeric(selected_label.split(" | ")[0], errors="coerce")
        selected = table.loc[table["player_id"] == selected_id].head(1)
        if not selected.empty:
            row = selected.iloc[0]
            left, right = st.columns([0.8, 1.2])
            with left:
                st.caption(f"{row['team_name']} - {row['position_group']} - {row['archetype']} - {float(row['minutes']):.0f} evidence minutes")
                st.plotly_chart(radar_figure(row), width="stretch", key=f"players_radar_{row['player_id']}")
            with right:
                z_rows = pd.DataFrame([
                    {"Metric group": SCORE_LABELS[column], "Z-score": float(row[column])}
                    for column in ZSCORE_COLUMNS
                    if column in row
                ]).sort_values("Z-score")
                fig = px.bar(
                    z_rows,
                    x="Z-score",
                    y="Metric group",
                    orientation="h",
                    color="Z-score",
                    color_continuous_scale=["#d6006c", "#f3f2f2", "#0088b0"],
                    title="Role-adjusted z-score profile",
                )
                fig.add_vline(x=0, line_dash="dot", line_color="#201e1d")
                fig.update_layout(height=420, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Z-score vs primary role average")
                st.plotly_chart(fig, width="stretch", key=f"players_z_bar_{row['player_id']}")

        z_pool = table.copy()
        axis_options = scatter_metric_options(z_pool)
        axis_cols = st.columns(2)
        with axis_cols[0]:
            player_x_label = st.selectbox("X-axis", list(axis_options), index=default_metric_index(axis_options, "volume_z_score"), key="players_x_axis")
        with axis_cols[1]:
            player_y_label = st.selectbox("Y-axis", list(axis_options), index=default_metric_index(axis_options, "intensity_z_score"), key="players_y_axis")
        player_x = axis_options[player_x_label]
        player_y = axis_options[player_y_label]
        z_pool["explosive_size"] = (pd.to_numeric(z_pool["explosiveness_z_score"], errors="coerce").fillna(0) + 3.2).clip(lower=0.2)
        fig = px.scatter(
            z_pool,
            x=player_x,
            y=player_y,
            size="explosive_size",
            color="position_group",
            hover_name="player_name",
            hover_data={"team_name": True, "profile_z_score": ":.2f", "explosiveness_z_score": ":.2f", "explosive_size": False},
            title=f"{metric_label(player_x)} vs {metric_label(player_y)}",
            labels={player_x: metric_label(player_x), player_y: metric_label(player_y), "position_group": "Primary role"},
        )
        if player_y.endswith("_z_score") or player_y.endswith("_z"):
            fig.add_hline(y=0, line_dash="dot", line_color="#201e1d")
        if player_x.endswith("_z_score") or player_x.endswith("_z"):
            fig.add_vline(x=0, line_dash="dot", line_color="#201e1d")
        fig.update_layout(height=560, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2")
        st.plotly_chart(fig, width="stretch", key="players_physical_z_scatter")

with tab_teams:
    team_totals = team_totals_frame(match_teams)
    if team_totals.empty:
        st.info("No team match data found. Run the refresh pipeline.")
    else:
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = px.bar(
                team_totals.sort_values("xthreat_total", ascending=True),
                x="xthreat_total",
                y="team_name",
                orientation="h",
                title="Total threat value by team",
                labels={"xthreat_total": "Threat value", "team_name": "Team"},
            )
            fig.update_layout(height=520, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Threat value")
            st.plotly_chart(fig, width="stretch", key="teams_threat_bar")
        with c2:
            fig = px.scatter(
                team_totals,
                x="high_intensity_runs",
                y="xthreat_total",
                size="off_ball_runs",
                color="dangerous_events",
                hover_name="team_name",
                hover_data={"events": True, "received_runs": True, "runs_per_possession": ":.3f", "threat_per_action": ":.4f"},
                title="Run intensity vs attacking threat",
                labels={"high_intensity_runs": "High-intensity runs", "xthreat_total": "Threat value", "dangerous_events": "Dangerous actions"},
            )
            fig.update_layout(height=520, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2")
            st.plotly_chart(fig, width="stretch", key="teams_intensity_threat_scatter")
        st.dataframe(
            team_totals.sort_values("xthreat_total", ascending=False),
            width="stretch",
            hide_index=True,
            column_config=COLUMN_CONFIG | {
                "runs_per_possession": st.column_config.NumberColumn("Runs per possession", format="%.3f"),
                "threat_per_action": st.column_config.NumberColumn("Threat per action", format="%.4f"),
            },
        )

with tab_archetypes:
    guide_left, guide_right = st.columns([1, 1])
    with guide_left:
        st.subheader("Archetype Mix")
        archetype_counts = filtered["archetype"].value_counts().reset_index()
        archetype_counts.columns = ["Archetype", "Players"]
        fig = px.bar(archetype_counts, x="Players", y="Archetype", orientation="h", title="Archetype mix in the current filter")
        fig.update_layout(height=360, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Players")
        st.plotly_chart(fig, width="stretch", key="archetypes_mix_chart")
    with guide_right:
        st.subheader("Score Shape")
        score_mix = filtered[SCORE_COLUMNS].mean().reset_index()
        score_mix.columns = ["Score", "Average"]
        score_mix["Score"] = score_mix["Score"].map(lambda value: SCORE_LABELS.get(value, value))
        fig = px.bar(score_mix, x="Average", y="Score", orientation="h", range_x=[0, 100], title="Average score family in current filter")
        fig.update_layout(height=360, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Position-group percentile score")
        st.plotly_chart(fig, width="stretch", key="archetypes_score_shape_chart")

    player_labels = filtered["profile_key"].tolist()
    selected_label = st.selectbox("Inspect player", player_labels if player_labels else [""])
    selected_id = pd.to_numeric(selected_label.split(" | ")[0], errors="coerce") if selected_label else None
    selected = filtered.loc[filtered["player_id"] == selected_id].head(1) if selected_id is not None else pd.DataFrame()

    if not selected.empty:
        row = selected.iloc[0]
        left, right = st.columns([0.95, 1.05])
        with left:
            st.subheader(row["player_name"])
            st.caption(f"{row['team_name']} - {row['position_group']} - {row['archetype']} - {float(row['minutes']):.0f} evidence minutes")
            st.plotly_chart(radar_figure(row), width="stretch", key=f"archetypes_radar_{row['player_id']}")
            render_archetype_panel(str(row["archetype"]))
        with right:
            profile_scores = pd.DataFrame([
                {"Score family": SCORE_LABELS[column], "Score": float(row[column])}
                for column in SCORE_COLUMNS
            ])
            fig = px.bar(profile_scores, x="Score", y="Score family", orientation="h", range_x=[0, 100], title="Why this profile stands out")
            fig.update_layout(height=360, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Position-group percentile score")
            st.plotly_chart(fig, width="stretch", key=f"archetypes_score_bar_{row['player_id']}")

            map_fig = px.scatter(
                filtered,
                x="map_x",
                y="map_y",
                color="archetype",
                size="profile_score",
                hover_name="player_name",
                hover_data={"team_name": True, "position_group": True, "minutes": ":.0f", "profile_score": ":.1f", "map_x": False, "map_y": False},
                labels={"archetype": "Archetype"},
                title="Role map from tactical score families",
            )
            map_fig.add_scatter(x=[row["map_x"]], y=[row["map_y"]], mode="markers", marker={"size": 18, "color": "#201e1d", "symbol": "x"}, name="Selected")
            map_fig.update_layout(height=480, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", xaxis_title="Profile map axis 1", yaxis_title="Profile map axis 2")
            st.plotly_chart(map_fig, width="stretch", key="archetypes_role_map")

        comp = filtered.copy()
        for column in SCORE_COLUMNS:
            comp[f"delta_{column}"] = (pd.to_numeric(comp[column], errors="coerce") - float(row[column])).abs()
        comp["similarity_gap"] = comp[[f"delta_{column}" for column in SCORE_COLUMNS]].mean(axis=1)
        st.subheader("Most Similar Profiles")
        st.dataframe(
            comp.loc[comp["player_id"] != row["player_id"]]
            .nsmallest(8, "similarity_gap")[["player_name", "team_name", "position_group", "archetype", "profile_score", "similarity_gap"]],
            width="stretch",
            hide_index=True,
            column_config=COLUMN_CONFIG,
        )

with tab_matches:
    match_label = st.selectbox("Match", matches["match_label"].tolist())
    match_id = int(matches.loc[matches["match_label"] == match_label, "match_id"].iloc[0])
    match_row = matches.loc[matches["match_id"] == match_id].iloc[0]
    match_events = events.loc[events["match_id"] == match_id].copy()
    match_runs = offball_runs.loc[offball_runs["match_id"] == match_id].copy()
    match_team_view = match_teams.loc[match_teams["match_id"] == match_id].copy()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Score", str(match_row["score"]))
    c2.metric("Actions", f"{int(match_row['events']):,}")
    c3.metric("Off-ball runs", f"{int(match_row['off_ball_runs']):,}")
    c4.metric("HI runs", f"{int(match_row['high_intensity_runs']):,}")
    c5.metric("Threat value", f"{float(match_row['xthreat_total']):.2f}")

    filter_cols = st.columns(4)
    with filter_cols[0]:
        team_filter = st.selectbox("Team", ["Both", *sorted(match_events["team_shortname"].dropna().astype(str).unique())])
    with filter_cols[1]:
        event_lookup = options_from_labels(match_events, "event_label", "event_type")
        event_choice = st.selectbox("Action type", ["All actions", *event_lookup.keys()])
    with filter_cols[2]:
        run_lookup = options_from_labels(match_runs, "run_type_label", "event_subtype")
        run_choice = st.selectbox("Run type", ["All run types", *run_lookup.keys()])
    with filter_cols[3]:
        speed_lookup = options_from_labels(match_runs, "speed_band_label", "speed_avg_band")
        speed_choice = st.selectbox("Speed band", ["All speeds", *speed_lookup.keys()])

    if team_filter != "Both":
        match_events = match_events.loc[match_events["team_shortname"] == team_filter]
        match_runs = match_runs.loc[match_runs["team_shortname"] == team_filter]
    if event_choice != "All actions":
        match_events = match_events.loc[match_events["event_type"] == event_lookup[event_choice]]
    if run_choice != "All run types":
        match_runs = match_runs.loc[match_runs["event_subtype"] == run_lookup[run_choice]]
    if speed_choice != "All speeds":
        match_runs = match_runs.loc[match_runs["speed_avg_band"] == speed_lookup[speed_choice]]

    pitch_col, inspect_col = st.columns([1.2, 0.9])
    selected_runs = pd.DataFrame(columns=match_runs.columns)
    selected_actions = pd.DataFrame(columns=match_events.columns)

    with inspect_col:
        st.subheader("Runs To Inspect")
        if match_runs.empty:
            st.info("No off-ball runs match the selected filters.")
        else:
            run_table = match_runs.sort_values(["dangerous", "received", "xthreat", "distance_covered"], ascending=False).head(16).reset_index(drop=True)
            run_selection = st.dataframe(
                run_table,
                width="stretch",
                hide_index=True,
                column_order=["time_start", "player_name", "team_shortname", "run_type_label", "speed_band_label", "distance_covered", "targeted", "received", "dangerous", "xthreat", "phase_label"],
                column_config=COLUMN_CONFIG,
                key=f"matches_runs_table_{match_id}",
                on_select="rerun",
                selection_mode="multi-row",
            )
            selected_runs = selected_dataframe_rows(run_selection, run_table)

        st.subheader("Highest Threat Actions")
        threat_table = match_events.sort_values("xthreat", ascending=False).head(12).reset_index(drop=True) if "xthreat" in match_events else pd.DataFrame()
        if threat_table.empty:
            st.info("No threat-valued actions match the selected filters.")
        else:
            action_selection = st.dataframe(
                threat_table,
                width="stretch",
                hide_index=True,
                column_order=["time_start", "event_label", "player_name", "team_shortname", "event_subtype", "xthreat", "dangerous", "third_start", "third_end"],
                column_config=COLUMN_CONFIG,
                key=f"matches_actions_table_{match_id}",
                on_select="rerun",
                selection_mode="multi-row",
            )
            selected_actions = selected_dataframe_rows(action_selection, threat_table)

    with pitch_col:
        pitch_title = f"{match_label}: filtered actions and off-ball movement"
        st.plotly_chart(
            match_activity_figure(match_events, match_runs, title=pitch_title, highlighted_events=selected_actions, highlighted_runs=selected_runs),
            width="stretch",
            key=f"matches_activity_map_{match_id}_{team_filter}_{event_choice}_{run_choice}_{speed_choice}",
        )

    left, right = st.columns([1.05, 0.95])
    with left:
        st.subheader("Team Match Profile")
        st.dataframe(
            match_team_view[[column for column in MATCH_TEAM_COLUMNS if column in match_team_view]],
            width="stretch",
            hide_index=True,
            column_config=COLUMN_CONFIG,
        )

    with right:
        phase_view = phases.loc[phases["match_id"] == match_id].copy()
        if not phase_view.empty:
            phase_counts = phase_view.groupby(["team_in_possession_shortname", "phase_label"], as_index=False)["duration"].sum()
            phase_counts["minutes"] = phase_counts["duration"] / 60
            fig = px.bar(
                phase_counts,
                x="phase_label",
                y="minutes",
                color="team_in_possession_shortname",
                barmode="group",
                title="Attacking phase minutes",
                labels={"phase_label": "Attacking phase", "minutes": "Minutes", "team_in_possession_shortname": "Club"},
            )
            fig.update_layout(height=420, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", xaxis_title="", yaxis_title="Minutes")
            st.plotly_chart(fig, width="stretch", key=f"matches_phase_minutes_{match_id}")


with tab_notes:
    st.subheader("Method")
    st.write(
        "The app consolidates each player into one sample-level profile before scoring. Physical, attacking movement and passing aggregate rows are combined by player ID; primary club and role are selected by evidence minutes; all observed clubs and roles remain visible. Players are then compared within their primary role group to build percentiles, z-scores, composite tactical scores and archetypes."
    )
    st.write(
        "Match views use compact exports from the full dynamic-event files rather than a capped sample. The off-ball run views expose subtype, zones, speed band, distance, receiving and targeting flags, dangerous flags, xThreat and phase context."
    )
    st.subheader("How The Archetypes Work")
    st.write(
        "Each player is compared with players in the same role group. The archetype describes the strongest tactical signal in that consolidated profile: movement behind, box movement, progression passing, linking play, repeat physical output, or a rounded contribution without a single dominant spike."
    )
    st.dataframe(archetype_guide_frame(), width="stretch", hide_index=True)
    st.subheader("Score Glossary")
    glossary = summary.get("metricGlossary", {})
    st.dataframe(
        pd.DataFrame([{"Score": metric_label(key), "What it means": value} for key, value in glossary.items()]),
        width="stretch",
        hide_index=True,
    )
    st.subheader("Source Limits")
    st.write(
        "The sample is 10 A-League matches plus season aggregate files from SkillCorner Open Data. Raw tracking requires Git LFS and includes the identity and smoothing caveats noted by SkillCorner. The dashboard should be read as a portfolio-grade analytical sample, not a production scouting model."
    )

    tracking = pd.DataFrame(summary.get("tracking", []))
    st.subheader("Tracking")
    if tracking.empty:
        st.info("No tracking status metadata found. Run the refresh pipeline.")
    else:
        tracking["tracking_label"] = tracking["tracking_status"].map(tracking_label)
        available_count = int((tracking["tracking_status"] == "available").sum())
        pointer_count = int((tracking["tracking_status"] == "lfs-pointer").sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Full tracking files", available_count)
        c2.metric("Git LFS placeholders", pointer_count)
        c3.metric("Matches checked", len(tracking))
        st.dataframe(
            tracking[["match_label", "tracking_label", "tracking_bytes"]],
            width="stretch",
            hide_index=True,
            column_config={
                "match_label": st.column_config.TextColumn("Match"),
                "tracking_label": st.column_config.TextColumn("Tracking status"),
                "tracking_bytes": st.column_config.NumberColumn("Local file size", format="%d bytes"),
            },
        )
        if pointer_count:
            st.markdown(
                "<p class='note'>The upstream tracking files are stored with Git LFS. This hosted sample keeps aggregate, phase and dynamic-event analysis fully available, and tracking-specific animation can activate in local checkouts with real JSONL files.</p>",
                unsafe_allow_html=True,
            )
