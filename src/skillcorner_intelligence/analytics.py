from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .data import (
    load_aggregate,
    load_dynamic_events,
    load_match_detail,
    load_matches,
    load_phases,
    tracking_status,
)
from .features import COMPOSITE_INPUTS, METRIC_GLOSSARY, add_composite_scores, add_metric_derivatives, assign_archetypes, to_numeric
from .paths import ANALYSIS_JSON, EVENT_SAMPLE_CSV, MATCH_SUMMARY_CSV, PHASE_TIMELINE_CSV, PLAYER_PROFILES_CSV, PROCESSED_DIR, TEAM_SUMMARY_CSV


def build_player_profiles() -> pd.DataFrame:
    physical = to_numeric(load_aggregate("physical")).rename(columns={"minutes_full_all": "minutes"})
    obr = to_numeric(load_aggregate("offball_runs"))
    passing = to_numeric(load_aggregate("passing"))

    identity = [column for column in physical.columns if column in {
        "player_id", "player_name", "player_short_name", "player_birthdate", "team_id", "team_name",
        "competition_name", "competition_id", "season_name", "season_id", "position_group", "minutes",
        "count_match", "count_match_failed",
    }]
    profiles = physical[identity + [column for column in physical.columns if column not in identity]].copy()

    obr_metric_columns = [column for column in obr.columns if column not in profiles.columns or column == "player_id"]
    passing_metric_columns = [column for column in passing.columns if column not in profiles.columns or column == "player_id"]
    profiles = profiles.merge(obr[["player_id", *[column for column in obr_metric_columns if column != "player_id"]]], on="player_id", how="left")
    profiles = profiles.merge(passing[["player_id", *[column for column in passing_metric_columns if column != "player_id"]]], on="player_id", how="left")
    profiles = profiles.fillna(0)

    metric_columns = sorted({column for columns in COMPOSITE_INPUTS.values() for column in columns if column in profiles})
    profiles = add_metric_derivatives(profiles, metric_columns)
    profiles = add_composite_scores(profiles)
    profiles = assign_archetypes(profiles)

    pca_columns = ["athletic_load_score", "sprint_threat_score", "off_ball_threat_score", "passing_progression_score", "reliability_score"]
    if len(profiles) >= 3:
        scaled = StandardScaler().fit_transform(profiles[pca_columns])
        components = PCA(n_components=2, random_state=42).fit_transform(scaled)
        profiles["map_x"] = components[:, 0].round(4)
        profiles["map_y"] = components[:, 1].round(4)
    else:
        profiles["map_x"] = 0.0
        profiles["map_y"] = 0.0

    return profiles.sort_values("profile_score", ascending=False)


def _team_name_map(matches: list[dict[str, Any]]) -> dict[int, str]:
    teams: dict[int, str] = {}
    for match in matches:
        teams[int(match["home_team"]["id"])] = match["home_team"]["short_name"]
        teams[int(match["away_team"]["id"])] = match["away_team"]["short_name"]
    return teams


def build_team_and_match_summaries() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matches = load_matches()
    teams = _team_name_map(matches)
    team_rows: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []
    event_samples: list[pd.DataFrame] = []
    phase_rows: list[pd.DataFrame] = []

    for match in matches:
        match_id = match["id"]
        detail = load_match_detail(match_id)
        phases = to_numeric(load_phases(match_id))
        events = to_numeric(load_dynamic_events(match_id))
        tracking = tracking_status(match_id)

        if not phases.empty:
            phase = phases.copy()
            phase["match_label"] = f'{match["home_team"]["short_name"]} v {match["away_team"]["short_name"]}'
            phase_rows.append(phase[[
                "match_id", "match_label", "period", "time_start", "time_end", "duration",
                "team_in_possession_id", "team_in_possession_shortname", "team_in_possession_phase_type",
                "team_out_of_possession_phase_type", "x_start", "y_start", "x_end", "y_end",
            ]])
            grouped = phase.groupby(["team_in_possession_id", "team_in_possession_shortname", "team_in_possession_phase_type"], dropna=False)["duration"].sum().reset_index()
            for row in grouped.to_dict("records"):
                team_rows.append({
                    "match_id": match_id,
                    "team_id": int(row["team_in_possession_id"]),
                    "team_name": row["team_in_possession_shortname"],
                    "phase_type": row["team_in_possession_phase_type"],
                    "phase_minutes": round(float(row["duration"]) / 60.0, 3),
                })

        if not events.empty:
            event_counts = events["event_type"].value_counts().to_dict() if "event_type" in events else {}
            danger = pd.to_numeric(events.get("dangerous", 0), errors="coerce").fillna(0).sum()
            xthreat = pd.to_numeric(events.get("xthreat", 0), errors="coerce").fillna(0).sum()
            match_rows.append({
                "match_id": match_id,
                "match_label": f'{match["home_team"]["short_name"]} v {match["away_team"]["short_name"]}',
                "date_time": match["date_time"],
                "score": f'{detail.get("home_team_score", "")}-{detail.get("away_team_score", "")}',
                "home_team": match["home_team"]["short_name"],
                "away_team": match["away_team"]["short_name"],
                "events": int(len(events)),
                "player_possessions": int(event_counts.get("player_possession", 0)),
                "off_ball_runs": int(event_counts.get("off_ball_run", 0)),
                "passing_options": int(event_counts.get("passing_option", 0)),
                "dangerous_events": int(danger),
                "xthreat_total": round(float(xthreat), 3),
                "tracking_status": tracking["status"],
                "tracking_bytes": tracking["bytes"],
            })
            sample_columns = [
                "event_id", "match_id", "period", "time_start", "event_type", "event_subtype", "player_name",
                "team_shortname", "x_start", "y_start", "x_end", "y_end", "dangerous", "targeted", "received",
                "xthreat", "team_in_possession_phase_type", "team_out_of_possession_phase_type",
            ]
            available = [column for column in sample_columns if column in events]
            sample = events.loc[
                events.get("event_type", pd.Series(index=events.index, dtype=object)).isin(["off_ball_run", "passing_option", "player_possession"])
            ].head(600)
            event_samples.append(sample[available])

    team_summary = pd.DataFrame(team_rows)
    if not team_summary.empty:
        team_summary = team_summary.groupby(["team_id", "team_name", "phase_type"], as_index=False)["phase_minutes"].sum()
        totals = team_summary.groupby("team_id")["phase_minutes"].transform("sum")
        team_summary["phase_share_pct"] = (team_summary["phase_minutes"] / totals.replace(0, np.nan) * 100).fillna(0).round(2)
    match_summary = pd.DataFrame(match_rows)
    event_sample = pd.concat(event_samples, ignore_index=True) if event_samples else pd.DataFrame()
    phase_timeline = pd.concat(phase_rows, ignore_index=True) if phase_rows else pd.DataFrame()
    return team_summary, match_summary, event_sample, phase_timeline


def write_outputs() -> dict[str, Any]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    profiles = build_player_profiles()
    team_summary, match_summary, event_sample, phase_timeline = build_team_and_match_summaries()

    profiles.to_csv(PLAYER_PROFILES_CSV, index=False)
    team_summary.to_csv(TEAM_SUMMARY_CSV, index=False)
    match_summary.to_csv(MATCH_SUMMARY_CSV, index=False)
    event_sample.to_csv(EVENT_SAMPLE_CSV, index=False)
    phase_timeline.to_csv(PHASE_TIMELINE_CSV, index=False)

    summary = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "source": "SkillCorner Open Data, AUS A-League 2024/2025",
        "rows": {
            "players": int(len(profiles)),
            "teams": int(team_summary["team_id"].nunique()) if not team_summary.empty else 0,
            "matches": int(len(match_summary)),
            "eventSample": int(len(event_sample)),
            "phaseRows": int(len(phase_timeline)),
        },
        "metricGlossary": METRIC_GLOSSARY,
        "topPlayers": profiles.head(10)[[
            "player_name", "team_name", "position_group", "profile_score", "archetype",
            "athletic_load_score", "off_ball_threat_score", "passing_progression_score",
        ]].to_dict("records"),
        "tracking": match_summary[["match_id", "match_label", "tracking_status", "tracking_bytes"]].to_dict("records") if not match_summary.empty else [],
    }
    ANALYSIS_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
