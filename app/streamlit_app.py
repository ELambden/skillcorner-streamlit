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
from skillcorner_intelligence.visualization import action_flow_figure, offball_run_figure, pitch_figure, radar_figure

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
        table[[column for column in PLAYER_TABLE_COLUMNS if column in table]].sort_values("profile_score", ascending=False),
        width="stretch",
        hide_index=True,
        column_config=COLUMN_CONFIG,
    )

with tab_archetypes:
    guide_left, guide_right = st.columns([1, 1])
    with guide_left:
        st.subheader("Archetype Mix")
        archetype_counts = filtered["archetype"].value_counts().reset_index()
        archetype_counts.columns = ["Archetype", "Players"]
        fig = px.bar(archetype_counts, x="Players", y="Archetype", orientation="h", title="Archetype mix in the current filter")
        fig.update_layout(height=360, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Players")
        st.plotly_chart(fig, width="stretch")
    with guide_right:
        st.subheader("Score Shape")
        score_mix = filtered[SCORE_COLUMNS].mean().reset_index()
        score_mix.columns = ["Score", "Average"]
        score_mix["Score"] = score_mix["Score"].map(lambda value: SCORE_LABELS.get(value, value))
        fig = px.bar(score_mix, x="Average", y="Score", orientation="h", range_x=[0, 100], title="Average score family in current filter")
        fig.update_layout(height=360, paper_bgcolor="#f3f2f2", plot_bgcolor="#f3f2f2", yaxis_title="", xaxis_title="Position-group percentile score")
        st.plotly_chart(fig, width="stretch")

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
                hover_data={"team_name": True, "position_group": True, "minutes": ":.0f", "profile_score": ":.1f", "map_x": False, "map_y": False},
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

    view_mode = st.radio("Pitch view", ["Action-specific detail", "Dynamic action flows", "Off-ball run paths", "Start-point map"], horizontal=True)
    selected_event_type = event_lookup.get(event_choice) if event_choice != "All actions" else ""
    if view_mode == "Action-specific detail" and selected_event_type == "off_ball_run":
        st.plotly_chart(offball_run_figure(match_runs, title=f"{match_label}: off-ball movement paths"), width="stretch")
    elif view_mode == "Off-ball run paths":
        st.plotly_chart(offball_run_figure(match_runs, title=f"{match_label}: off-ball run paths"), width="stretch")
    elif view_mode == "Start-point map":
        st.plotly_chart(pitch_figure(match_events, title=f"{match_label}: action start points"), width="stretch")
    else:
        title_suffix = event_choice.lower() if event_choice != "All actions" else "dynamic action flows"
        st.plotly_chart(action_flow_figure(match_events, title=f"{match_label}: {title_suffix}"), width="stretch")

    left, right = st.columns([1.05, 0.95])
    with left:
        st.subheader("Team Match Profile")
        st.dataframe(
            match_team_view[[column for column in MATCH_TEAM_COLUMNS if column in match_team_view]],
            width="stretch",
            hide_index=True,
            column_config=COLUMN_CONFIG,
        )

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

    with right:
        st.subheader("Runs To Inspect")
        if match_runs.empty:
            st.info("No off-ball runs match the selected filters.")
        else:
            run_table = match_runs.sort_values(["dangerous", "received", "xthreat", "distance_covered"], ascending=False)
            st.dataframe(
                run_table[["time_start", "player_name", "team_shortname", "run_type_label", "speed_band_label", "distance_covered", "targeted", "received", "dangerous", "xthreat", "phase_label"]].head(16),
                width="stretch",
                hide_index=True,
                column_config=COLUMN_CONFIG,
            )

        st.subheader("Highest Threat Actions")
        threat_table = match_events.sort_values("xthreat", ascending=False).head(12) if "xthreat" in match_events else pd.DataFrame()
        if threat_table.empty:
            st.info("No threat-valued actions match the selected filters.")
        else:
            st.dataframe(
                threat_table[["time_start", "event_label", "player_name", "team_shortname", "event_subtype", "xthreat", "dangerous", "third_start", "third_end"]],
                width="stretch",
                hide_index=True,
                column_config=COLUMN_CONFIG,
            )

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
                "<p class='note'>The upstream tracking files are stored with Git LFS. This hosted sample keeps aggregate, phase and dynamic-event analysis fully available, and tracking-specific animation can activate in local checkouts with real JSONL files.</p>",
                unsafe_allow_html=True,
            )

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
