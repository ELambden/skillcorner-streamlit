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
    PHASE_TIMELINE_CSV,
    PLAYER_PROFILES_CSV,
    TEAM_SUMMARY_CSV,
)
from skillcorner_intelligence.visualization import pitch_figure, radar_figure

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
.status-ok { color: #007f5f; font-weight: 700; }
.status-warn { color: #a05a00; font-weight: 700; }
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


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Missing {path}. Run `python scripts/refresh_all.py`.")
        st.stop()
    frame = pd.read_csv(path)
    for column in frame.columns:
        if column not in {"player_name", "player_short_name", "team_name", "position_group", "archetype", "phase_type", "match_label", "event_type", "event_subtype", "time_start"}:
            converted = pd.to_numeric(frame[column], errors="coerce")
            if converted.notna().any():
                frame[column] = converted
    return frame


@st.cache_data(show_spinner=False)
def load_summary() -> dict[str, Any]:
    if not ANALYSIS_JSON.exists():
        return {}
    return json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))


players = load_csv(PLAYER_PROFILES_CSV)
teams = load_csv(TEAM_SUMMARY_CSV)
matches = load_csv(MATCH_SUMMARY_CSV)
events = load_csv(EVENT_SAMPLE_CSV)
phases = load_csv(PHASE_TIMELINE_CSV)
summary = load_summary()

st.title("SkillCorner Football Intelligence Lab")
st.caption("A-League 2024/2025 open-data analysis across physical outputs, off-ball runs, passing, phases of play and dynamic events.")

with st.sidebar:
    st.header("Filters")
    positions = ["All", *sorted(players["position_group"].dropna().astype(str).unique())]
    teams_filter = ["All", *sorted(players["team_name"].dropna().astype(str).unique())]
    position = st.selectbox("Position group", positions)
    team = st.selectbox("Team", teams_filter)
    min_minutes = st.slider("Minimum minutes", 0, int(max(players["minutes"].max(), 1)), 60, 30)
    min_profile = st.slider("Minimum profile score", 0, 100, 0, 5)

filtered = players.copy()
if position != "All":
    filtered = filtered.loc[filtered["position_group"] == position]
if team != "All":
    filtered = filtered.loc[filtered["team_name"] == team]
filtered = filtered.loc[(filtered["minutes"] >= min_minutes) & (filtered["profile_score"] >= min_profile)]

tab_league, tab_players, tab_archetypes, tab_matches, tab_tracking, tab_notes = st.tabs([
    "League Lens",
    "Player Finder",
    "Archetype Lab",
    "Match Intelligence",
    "Tracking Room",
    "Method Notes",
])

with tab_league:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Players", f"{len(players):,}")
    c2.metric("Teams", f"{players['team_id'].nunique():,}")
    c3.metric("Matches", f"{len(matches):,}")
    c4.metric("Dynamic events sampled", f"{len(events):,}")

    left, right = st.columns([1.15, 1])
    with left:
        top = filtered.nlargest(20, "profile_score")
        fig = px.bar(
            top.sort_values("profile_score"),
            x="profile_score",
            y="player_short_name",
            color="archetype",
            orientation="h",
            hover_data=["player_name", "team_name", "position_group"],
            title="Top filtered player profiles",
        )
        fig.update_layout(height=620, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Profile score")
        st.plotly_chart(fig, width="stretch")
    with right:
        phase_total = teams.groupby(["team_name", "phase_type"], as_index=False)["phase_minutes"].sum()
        selected_phase = st.selectbox("Team phase view", sorted(phase_total["phase_type"].dropna().unique()))
        phase_view = phase_total.loc[phase_total["phase_type"] == selected_phase].sort_values("phase_minutes", ascending=False)
        fig = px.bar(phase_view, x="phase_minutes", y="team_name", orientation="h", title=f"{selected_phase} minutes by team")
        fig.update_layout(height=620, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Minutes")
        st.plotly_chart(fig, width="stretch")

with tab_players:
    search = st.text_input("Search player or club", "")
    table = filtered.copy()
    if search:
        mask = (
            table["player_name"].astype(str).str.contains(search, case=False, na=False)
            | table["team_name"].astype(str).str.contains(search, case=False, na=False)
            | table["archetype"].astype(str).str.contains(search, case=False, na=False)
        )
        table = table.loc[mask]

    st.dataframe(
        table[[
            "player_name", "team_name", "position_group", "minutes", "archetype", "profile_score",
            "athletic_load_score", "sprint_threat_score", "off_ball_threat_score", "passing_progression_score",
            "psv99", "total_metersperminute_full_all", "pass_pct_completed",
        ]].sort_values("profile_score", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "profile_score": st.column_config.ProgressColumn("Profile", min_value=0, max_value=100, format="%.1f"),
            "athletic_load_score": st.column_config.ProgressColumn("Athletic", min_value=0, max_value=100, format="%.1f"),
            "sprint_threat_score": st.column_config.ProgressColumn("Sprint", min_value=0, max_value=100, format="%.1f"),
            "off_ball_threat_score": st.column_config.ProgressColumn("Off-ball", min_value=0, max_value=100, format="%.1f"),
            "passing_progression_score": st.column_config.ProgressColumn("Passing", min_value=0, max_value=100, format="%.1f"),
        },
    )

with tab_archetypes:
    player_labels = (filtered["player_name"] + " | " + filtered["team_name"] + " | " + filtered["position_group"]).tolist()
    selected_label = st.selectbox("Player profile", player_labels if player_labels else [""])
    selected_name = selected_label.split(" | ")[0] if selected_label else ""
    selected = filtered.loc[filtered["player_name"] == selected_name].head(1)

    left, right = st.columns([0.95, 1.05])
    if not selected.empty:
        row = selected.iloc[0]
        with left:
            st.subheader(row["player_name"])
            st.caption(f"{row['team_name']} · {row['position_group']} · {row['archetype']}")
            st.plotly_chart(radar_figure(row), width="stretch")
        with right:
            fig = px.scatter(
                filtered,
                x="map_x",
                y="map_y",
                color="archetype",
                size="profile_score",
                hover_name="player_name",
                hover_data=["team_name", "position_group", *SCORE_COLUMNS],
                title="Role map from composite profile scores",
            )
            fig.add_scatter(x=[row["map_x"]], y=[row["map_y"]], mode="markers", marker={"size": 18, "color": "#201e1d", "symbol": "x"}, name="Selected")
            fig.update_layout(height=520, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2")
            st.plotly_chart(fig, width="stretch")

        comp = filtered.copy()
        for column in SCORE_COLUMNS:
            comp[f"delta_{column}"] = (pd.to_numeric(comp[column], errors="coerce") - float(row[column])).abs()
        comp["similarity_gap"] = comp[[f"delta_{column}" for column in SCORE_COLUMNS]].mean(axis=1)
        st.dataframe(
            comp.loc[comp["player_name"] != row["player_name"]]
            .nsmallest(8, "similarity_gap")[["player_name", "team_name", "position_group", "archetype", "profile_score", "similarity_gap"]],
            width="stretch",
            hide_index=True,
        )

with tab_matches:
    match_label = st.selectbox("Match", matches["match_label"].tolist())
    match_id = int(matches.loc[matches["match_label"] == match_label, "match_id"].iloc[0])
    match_events = events.loc[events["match_id"] == match_id].copy()
    event_types = ["All", *sorted(match_events["event_type"].dropna().astype(str).unique())]
    event_type = st.selectbox("Event type", event_types)
    if event_type != "All":
        match_events = match_events.loc[match_events["event_type"] == event_type]

    c1, c2, c3, c4 = st.columns(4)
    match_row = matches.loc[matches["match_id"] == match_id].iloc[0]
    c1.metric("Score", str(match_row["score"]))
    c2.metric("Events", f"{int(match_row['events']):,}")
    c3.metric("Dangerous", f"{int(match_row['dangerous_events']):,}")
    c4.metric("xThreat", f"{float(match_row['xthreat_total']):.2f}")
    st.plotly_chart(pitch_figure(match_events, title=match_label), width="stretch")

    phase_view = phases.loc[phases["match_id"] == match_id].copy()
    if not phase_view.empty:
        phase_counts = phase_view.groupby(["team_in_possession_shortname", "team_in_possession_phase_type"], as_index=False)["duration"].sum()
        phase_counts["minutes"] = phase_counts["duration"] / 60
        fig = px.bar(phase_counts, x="team_in_possession_phase_type", y="minutes", color="team_in_possession_shortname", barmode="group", title="Phase minutes")
        fig.update_layout(height=420, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", xaxis_title="", yaxis_title="Minutes")
        st.plotly_chart(fig, width="stretch")

with tab_tracking:
    tracking = pd.DataFrame(summary.get("tracking", []))
    if tracking.empty:
        st.info("No tracking status metadata found. Run the refresh pipeline.")
    else:
        available_count = int((tracking["tracking_status"] == "available").sum())
        pointer_count = int((tracking["tracking_status"] == "lfs-pointer").sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Available tracking files", available_count)
        c2.metric("LFS pointer files", pointer_count)
        c3.metric("Matches checked", len(tracking))
        st.dataframe(tracking, width="stretch", hide_index=True)
        if pointer_count:
            st.markdown(
                "<p class='note'>Tracking JSONL is stored with Git LFS upstream. Pull real LFS objects locally, rerun "
                "<code>python scripts/refresh_all.py</code>, and this tab can be extended to animate sampled frames.</p>",
                unsafe_allow_html=True,
            )

with tab_notes:
    st.subheader("Method")
    st.write(
        "This app goes beyond the tutorial notebooks by joining physical, off-ball run and passing aggregates, "
        "normalizing metrics within position groups, creating composite analyst scores, and adding phase/event-level match views."
    )
    st.subheader("Glossary")
    glossary = summary.get("metricGlossary", {})
    st.dataframe(pd.DataFrame([{"metric": key, "description": value} for key, value in glossary.items()]), width="stretch", hide_index=True)
    st.subheader("Source limits")
    st.write(
        "The sample is 10 A-League matches plus season aggregate files from SkillCorner Open Data. "
        "Raw tracking requires Git LFS and includes known identity/smoothing limitations from the upstream data notes."
    )
