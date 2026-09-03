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
from skillcorner_intelligence.presentation import (
    ARCHETYPE_DEFINITIONS,
    SCORE_LABELS,
    defensive_phase_label,
    event_label,
    metric_label,
    phase_label,
    tracking_label,
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

PLAYER_TABLE_COLUMNS = [
    "player_name",
    "team_name",
    "position_group",
    "minutes",
    "archetype",
    "profile_score",
    "athletic_load_score",
    "sprint_threat_score",
    "off_ball_threat_score",
    "passing_progression_score",
    "psv99",
    "total_metersperminute_full_all",
    "pass_pct_completed",
]

COLUMN_CONFIG = {
    "player_name": st.column_config.TextColumn("Player"),
    "team_name": st.column_config.TextColumn("Club"),
    "position_group": st.column_config.TextColumn("Role group"),
    "minutes": st.column_config.NumberColumn("Minutes", format="%.0f"),
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
}


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Missing {path}. Run `python scripts/refresh_all.py`.")
        st.stop()
    frame = pd.read_csv(path)
    text_columns = {
        "player_name", "player_short_name", "team_name", "position_group", "archetype", "phase_type",
        "phase_label", "match_label", "event_type", "event_label", "event_subtype", "time_start",
        "team_in_possession_phase_type", "team_out_of_possession_phase_type", "tracking_status", "tracking_label",
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


def prepare_display_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    players = load_csv(PLAYER_PROFILES_CSV).copy()
    teams = load_csv(TEAM_SUMMARY_CSV).copy()
    matches = load_csv(MATCH_SUMMARY_CSV).copy()
    events = load_csv(EVENT_SAMPLE_CSV).copy()
    phases = load_csv(PHASE_TIMELINE_CSV).copy()
    summary = load_summary()

    teams["phase_label"] = teams["phase_type"].map(phase_label)
    events["event_label"] = events["event_type"].map(event_label)
    if "event_subtype" in events:
        events["action_detail"] = events["event_subtype"].fillna("").map(lambda value: str(value).replace("_", " ").title() if value else "")
    phases["phase_label"] = phases["team_in_possession_phase_type"].map(phase_label)
    phases["defensive_shape_label"] = phases["team_out_of_possession_phase_type"].map(defensive_phase_label)
    matches["tracking_label"] = matches["tracking_status"].map(tracking_label)
    players["profile_key"] = players.index.astype(str) + " | " + players["player_name"].astype(str) + " | " + players["team_name"].astype(str)
    return players, teams, matches, events, phases, summary


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


players, teams, matches, events, phases, summary = prepare_display_data()

st.title("SkillCorner Football Intelligence Lab")
st.caption("A-League 2024/2025 open-data analysis across physical output, attacking movement, passing, tactical phases and match actions.")

with st.sidebar:
    st.header("Filters")
    positions = ["All", *sorted(players["position_group"].dropna().astype(str).unique())]
    team_options = ["All", *sorted(players["team_name"].dropna().astype(str).unique())]
    position = st.selectbox("Role group", positions)
    team = st.selectbox("Club", team_options)
    min_minutes = st.slider("Minimum minutes", 0, int(max(players["minutes"].max(), 1)), 60, 30)
    min_profile = st.slider("Minimum overall profile", 0, 100, 0, 5)

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
    c2.metric("Clubs", f"{players['team_id'].nunique():,}")
    c3.metric("Matches", f"{len(matches):,}")
    c4.metric("Sampled match actions", f"{len(events):,}")

    left, right = st.columns([1.15, 1])
    with left:
        top = filtered.nlargest(20, "profile_score")
        fig = px.bar(
            top.sort_values("profile_score"),
            x="profile_score",
            y="player_short_name",
            color="archetype",
            orientation="h",
            hover_data={"player_name": True, "team_name": True, "position_group": True, "profile_score": ":.1f", "player_short_name": False},
            labels={"profile_score": "Overall profile", "player_short_name": "Player", "archetype": "Archetype"},
            title="Top player profiles in the current filter",
        )
        fig.update_layout(height=620, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Overall profile")
        st.plotly_chart(fig, width="stretch")
    with right:
        phase_total = teams.groupby(["team_name", "phase_type", "phase_label"], as_index=False)["phase_minutes"].sum()
        phase_options = sorted(phase_total["phase_label"].dropna().unique())
        selected_phase_label = st.selectbox("Attacking phase", phase_options)
        phase_view = phase_total.loc[phase_total["phase_label"] == selected_phase_label].sort_values("phase_minutes", ascending=False)
        fig = px.bar(
            phase_view,
            x="phase_minutes",
            y="team_name",
            orientation="h",
            title=f"{selected_phase_label} minutes by club",
            labels={"phase_minutes": "Minutes", "team_name": "Club"},
        )
        fig.update_layout(height=620, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Minutes")
        st.plotly_chart(fig, width="stretch")

with tab_players:
    search = st.text_input("Search player, club or archetype", "")
    table = filtered.copy()
    if search:
        mask = (
            table["player_name"].astype(str).str.contains(search, case=False, na=False)
            | table["team_name"].astype(str).str.contains(search, case=False, na=False)
            | table["archetype"].astype(str).str.contains(search, case=False, na=False)
        )
        table = table.loc[mask]

    st.dataframe(
        table[PLAYER_TABLE_COLUMNS].sort_values("profile_score", ascending=False),
        width="stretch",
        hide_index=True,
        column_config=COLUMN_CONFIG,
    )

with tab_archetypes:
    st.subheader("How the archetypes work")
    st.write(
        "Each player is first compared with players in the same role group. The archetype then describes the strongest tactical signal in that profile: movement behind, box movement, progression passing, linking play, repeat physical output, or a rounded contribution without a single dominant spike."
    )

    guide_left, guide_right = st.columns([1, 1])
    with guide_left:
        st.dataframe(archetype_guide_frame(), width="stretch", hide_index=True)
    with guide_right:
        archetype_counts = filtered["archetype"].value_counts().reset_index()
        archetype_counts.columns = ["Archetype", "Players"]
        fig = px.bar(archetype_counts, x="Players", y="Archetype", orientation="h", title="Archetype mix in the current filter")
        fig.update_layout(height=360, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Players")
        st.plotly_chart(fig, width="stretch")

    player_labels = filtered["profile_key"].tolist()
    selected_label = st.selectbox("Inspect player", player_labels if player_labels else [""])
    selected_index = int(selected_label.split(" | ")[0]) if selected_label else -1
    selected = filtered.loc[filtered.index == selected_index].head(1)

    if not selected.empty:
        row = selected.iloc[0]
        left, right = st.columns([0.95, 1.05])
        with left:
            st.subheader(row["player_name"])
            st.caption(f"{row['team_name']} - {row['position_group']} - {row['archetype']}")
            st.plotly_chart(radar_figure(row), width="stretch")
            render_archetype_panel(str(row["archetype"]))
        with right:
            profile_scores = pd.DataFrame([
                {"Score family": SCORE_LABELS[column], "Score": float(row[column])}
                for column in SCORE_COLUMNS
            ])
            fig = px.bar(profile_scores, x="Score", y="Score family", orientation="h", range_x=[0, 100], title="Why this profile stands out")
            fig.update_layout(height=360, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Position-group percentile score")
            st.plotly_chart(fig, width="stretch")

            map_fig = px.scatter(
                filtered,
                x="map_x",
                y="map_y",
                color="archetype",
                size="profile_score",
                hover_name="player_name",
                hover_data={"team_name": True, "position_group": True, "profile_score": ":.1f", "map_x": False, "map_y": False},
                labels={"archetype": "Archetype"},
                title="Role map from tactical score families",
            )
            map_fig.add_scatter(x=[row["map_x"]], y=[row["map_y"]], mode="markers", marker={"size": 18, "color": "#201e1d", "symbol": "x"}, name="Selected")
            map_fig.update_layout(height=480, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", xaxis_title="Profile map axis 1", yaxis_title="Profile map axis 2")
            st.plotly_chart(map_fig, width="stretch")

        comp = filtered.copy()
        for column in SCORE_COLUMNS:
            comp[f"delta_{column}"] = (pd.to_numeric(comp[column], errors="coerce") - float(row[column])).abs()
        comp["similarity_gap"] = comp[[f"delta_{column}" for column in SCORE_COLUMNS]].mean(axis=1)
        st.subheader("Most similar profiles")
        st.dataframe(
            comp.loc[comp.index != selected_index]
            .nsmallest(8, "similarity_gap")[["player_name", "team_name", "position_group", "archetype", "profile_score", "similarity_gap"]],
            width="stretch",
            hide_index=True,
            column_config=COLUMN_CONFIG,
        )

with tab_matches:
    match_label = st.selectbox("Match", matches["match_label"].tolist())
    match_id = int(matches.loc[matches["match_label"] == match_label, "match_id"].iloc[0])
    match_events = events.loc[events["match_id"] == match_id].copy()
    event_lookup = {event_label(value): value for value in sorted(match_events["event_type"].dropna().astype(str).unique())}
    event_choice = st.selectbox("Action type", ["All actions", *sorted(event_lookup)])
    if event_choice != "All actions":
        match_events = match_events.loc[match_events["event_type"] == event_lookup[event_choice]]

    c1, c2, c3, c4 = st.columns(4)
    match_row = matches.loc[matches["match_id"] == match_id].iloc[0]
    c1.metric("Score", str(match_row["score"]))
    c2.metric("Actions", f"{int(match_row['events']):,}")
    c3.metric("Dangerous actions", f"{int(match_row['dangerous_events']):,}")
    c4.metric("Threat value", f"{float(match_row['xthreat_total']):.2f}")
    st.plotly_chart(pitch_figure(match_events, title=match_label), width="stretch")

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
        st.plotly_chart(fig, width="stretch")

with tab_tracking:
    tracking = pd.DataFrame(summary.get("tracking", []))
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
                "<p class='note'>The upstream tracking files are stored with Git LFS. The current checkout has lightweight placeholders, so this version keeps the full aggregate, phase and action analysis available while reserving tracking animation for local checkouts with real LFS objects.</p>",
                unsafe_allow_html=True,
            )

with tab_notes:
    st.subheader("Method")
    st.write(
        "The app joins physical, attacking movement and passing aggregates, compares players within their role group, then builds composite tactical scores. Match views use dynamic actions and phases of play to show where attacks developed and which broad tactical states appeared most often."
    )
    st.subheader("Score Glossary")
    glossary = summary.get("metricGlossary", {})
    st.dataframe(
        pd.DataFrame([{"Score": metric_label(key), "What it means": value} for key, value in glossary.items()]),
        width="stretch",
        hide_index=True,
    )
    st.subheader("Source Limits")
    st.write(
        "The sample is 10 A-League matches plus season aggregate files from SkillCorner Open Data. Raw tracking requires Git LFS and includes the identity and smoothing caveats noted by SkillCorner."
    )
