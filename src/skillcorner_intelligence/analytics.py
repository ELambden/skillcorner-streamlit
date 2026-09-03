from __future__ import annotations

import json
from datetime import UTC, datetime
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
from .presentation import ARCHETYPE_DEFINITIONS, EVENT_TYPE_LABELS, IN_POSSESSION_PHASE_LABELS, TRACKING_STATUS_LABELS
from .paths import (
    ANALYSIS_JSON,
    EVENT_SAMPLE_CSV,
    MATCH_SUMMARY_CSV,
    MATCH_TEAM_SUMMARY_CSV,
    OFFBALL_RUNS_CSV,
    PHASE_TIMELINE_CSV,
    PLAYER_PROFILES_CSV,
    PROCESSED_DIR,
    TEAM_SUMMARY_CSV,
)

PROFILE_TEXT_COLUMNS = {
    "player_name",
    "player_short_name",
    "player_birthdate",
    "team_name",
    "competition_name",
    "season_name",
    "position_group",
}

AGGREGATE_CONTEXT_COLUMNS = {
    "competition_id",
    "competition_edition_id",
    "competition_name",
    "season_id",
    "season_name",
    "team_id",
    "team_name",
    "player_name",
    "player_short_name",
    "player_birthdate",
    "position_group",
    "minutes_full_all",
    "minutes_tip",
    "minutes_otip",
    "count_match",
    "count_match_failed",
    "performance_count",
    "performance_included_count",
    "performance_failed_count",
}

EVENT_EXPORT_COLUMNS = [
    "event_id",
    "match_id",
    "period",
    "time_start",
    "time_end",
    "minute_start",
    "second_start",
    "frame_start",
    "frame_end",
    "event_type",
    "event_subtype",
    "player_id",
    "player_name",
    "player_in_possession_id",
    "player_in_possession_name",
    "team_id",
    "team_shortname",
    "x_start",
    "y_start",
    "x_end",
    "y_end",
    "channel_start",
    "channel_end",
    "third_start",
    "third_end",
    "penalty_area_start",
    "penalty_area_end",
    "distance_covered",
    "speed_avg",
    "speed_avg_band",
    "trajectory_direction",
    "pass_outcome",
    "pass_distance",
    "pass_range",
    "targeted",
    "received",
    "received_in_space",
    "dangerous",
    "difficult_pass_target",
    "xthreat",
    "xpass_completion",
    "passing_option_score",
    "n_passing_options",
    "n_off_ball_runs",
    "n_opponents_bypassed",
    "associated_off_ball_run_event_id",
    "associated_off_ball_run_subtype",
    "team_in_possession_phase_type",
    "team_out_of_possession_phase_type",
]

OFFBALL_EXPORT_COLUMNS = [
    "event_id",
    "match_id",
    "match_label",
    "period",
    "time_start",
    "time_end",
    "frame_start",
    "frame_end",
    "player_id",
    "player_name",
    "team_id",
    "team_shortname",
    "event_subtype",
    "x_start",
    "y_start",
    "x_end",
    "y_end",
    "channel_start",
    "channel_end",
    "third_start",
    "third_end",
    "penalty_area_start",
    "penalty_area_end",
    "distance_covered",
    "speed_avg",
    "speed_avg_band",
    "trajectory_direction",
    "targeted",
    "received",
    "received_in_space",
    "dangerous",
    "xthreat",
    "team_in_possession_phase_type",
    "team_out_of_possession_phase_type",
    "high_intensity",
]


def _numeric_column(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _first_valid(series: pd.Series) -> Any:
    values = series.dropna()
    values = values.loc[values.astype(str).str.len() > 0]
    return values.iloc[0] if not values.empty else ""


def _unique_join(series: pd.Series) -> str:
    values = series.dropna().astype(str)
    values = [value for value in values if value and value != "0"]
    return "; ".join(sorted(dict.fromkeys(values)))


def _profile_keys(frame: pd.DataFrame) -> pd.Series:
    ids = frame.get("player_id", pd.Series(index=frame.index, dtype=object)).astype(str).str.strip()
    names = frame.get("player_name", pd.Series("", index=frame.index)).astype(str).str.lower().str.strip()
    births = frame.get("player_birthdate", pd.Series("", index=frame.index)).astype(str).str.strip()
    return np.where(ids.ne("") & ids.ne("nan") & ids.ne("None"), "id:" + ids, "name:" + names + "|" + births)


def _source_weights(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    result = frame.copy()
    if source == "physical":
        appearances = _numeric_column(result, "count_match", 1.0).replace(0, 1.0)
        minutes = _numeric_column(result, "minutes_full_all", 0.0)
        context = minutes * appearances
        result["_context_weight"] = context.where(context > 0, appearances)
        result["_tip_weight"] = result["_context_weight"]
        result["_otip_weight"] = result["_context_weight"]
        result["_evidence_minutes"] = result["_context_weight"]
    else:
        appearances = _numeric_column(result, "performance_included_count", 0.0)
        appearances = appearances.where(appearances > 0, _numeric_column(result, "performance_count", 1.0)).replace(0, 1.0)
        tip = _numeric_column(result, "minutes_tip", 0.0) * appearances
        otip = _numeric_column(result, "minutes_otip", 0.0) * appearances
        result["_tip_weight"] = tip.where(tip > 0, appearances)
        result["_otip_weight"] = otip.where(otip > 0, appearances)
        context = tip + otip
        result["_context_weight"] = context.where(context > 0, appearances)
        result["_evidence_minutes"] = tip + otip
    return result


def _weighted_average(series: pd.Series, weights: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce")
    mask = values.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return 0.0
    return float(np.average(values.loc[mask], weights=weights.loc[mask]))


def _primary_value(group: pd.DataFrame, column: str) -> Any:
    if column not in group:
        return ""
    weights = _numeric_column(group, "_context_weight", 1.0)
    values = group[column]
    frame = pd.DataFrame({"value": values, "weight": weights}).dropna()
    frame = frame.loc[frame["value"].astype(str).str.len() > 0]
    if frame.empty:
        return ""
    ranked = frame.groupby("value", dropna=False)["weight"].sum().sort_values(ascending=False)
    return ranked.index[0]


def _aggregation_weight(group: pd.DataFrame, column: str) -> pd.Series:
    if "_p30tip" in column or column.endswith("_tip") or "_tip_" in column:
        return _numeric_column(group, "_tip_weight", 1.0)
    if "_otip" in column:
        return _numeric_column(group, "_otip_weight", 1.0)
    return _numeric_column(group, "_context_weight", 1.0)


def _is_summed_metric(column: str) -> bool:
    return column in {
        "count_match",
        "count_match_failed",
        "performance_count",
        "performance_included_count",
        "performance_failed_count",
        "offballrun_count_total",
        "passopportunity_count_total",
        "pass_count_attempted_total",
    }


def _is_peak_metric(column: str) -> bool:
    return column in {"psv99", "psv99_top5"}


def consolidate_player_aggregate(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    """Collapse SkillCorner context rows into one analytical row per player."""
    if frame.empty:
        return frame.copy()

    prepared = _source_weights(frame.copy(), source)
    prepared["_profile_key"] = _profile_keys(prepared)
    rows: list[dict[str, Any]] = []

    for _, group in prepared.groupby("_profile_key", sort=False, dropna=False):
        row: dict[str, Any] = {
            "player_id": _first_valid(group.get("player_id", pd.Series(dtype=object))),
            "player_name": _first_valid(group.get("player_name", pd.Series(dtype=object))),
            "player_short_name": _first_valid(group.get("player_short_name", pd.Series(dtype=object))),
            "player_birthdate": _first_valid(group.get("player_birthdate", pd.Series(dtype=object))),
            "team_id": _primary_value(group, "team_id"),
            "team_name": _primary_value(group, "team_name"),
            "teams_played": _unique_join(group.get("team_name", pd.Series(dtype=object))),
            "position_group": _primary_value(group, "position_group"),
            "position_groups": _unique_join(group.get("position_group", pd.Series(dtype=object))),
            "profile_context_count": int(len(group)),
            "minutes": round(float(_numeric_column(group, "_evidence_minutes", 0.0).sum()), 2),
        }
        if "count_match" in group:
            row["count_match"] = int(round(float(_numeric_column(group, "count_match", 0.0).sum())))

        for column in group.columns:
            if column.startswith("_") or column in row or column in AGGREGATE_CONTEXT_COLUMNS:
                continue
            series = group[column]
            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().any():
                if _is_summed_metric(column):
                    row[column] = round(float(numeric.fillna(0.0).sum()), 4)
                elif _is_peak_metric(column):
                    row[column] = round(float(numeric.max()), 4)
                else:
                    row[column] = round(_weighted_average(series, _aggregation_weight(group, column)), 4)
            elif column in PROFILE_TEXT_COLUMNS:
                row[column] = _first_valid(series)
        rows.append(row)

    return pd.DataFrame(rows)


def build_player_profiles() -> pd.DataFrame:
    physical = consolidate_player_aggregate(to_numeric(load_aggregate("physical")).rename(columns={"minutes_full_all": "minutes_full_all"}), "physical")
    obr = consolidate_player_aggregate(to_numeric(load_aggregate("offball_runs")), "offball_runs")
    passing = consolidate_player_aggregate(to_numeric(load_aggregate("passing")), "passing")

    profiles = physical.copy()
    for aggregate in [obr, passing]:
        if aggregate.empty:
            continue
        metric_columns = [column for column in aggregate.columns if column not in profiles.columns and column != "player_id"]
        profiles = profiles.merge(aggregate[["player_id", *metric_columns]], on="player_id", how="left")
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


def _match_label(match: dict[str, Any]) -> str:
    return f'{match["home_team"]["short_name"]} v {match["away_team"]["short_name"]}'


def _event_count(events: pd.DataFrame, event_type: str) -> int:
    if "event_type" not in events:
        return 0
    return int((events["event_type"] == event_type).sum())


def _bool_sum(frame: pd.DataFrame, column: str) -> int:
    return int(_numeric_column(frame, column, 0.0).sum())


def _xthreat_sum(frame: pd.DataFrame) -> float:
    return round(float(_numeric_column(frame, "xthreat", 0.0).sum()), 3)


def _high_intensity_mask(frame: pd.DataFrame) -> pd.Series:
    if "speed_avg_band" not in frame:
        return pd.Series(False, index=frame.index)
    return frame["speed_avg_band"].astype(str).str.lower().isin({"hsr", "sprinting", "sprint"})


def _summarise_events(frame: pd.DataFrame) -> dict[str, Any]:
    off_ball = frame.loc[frame.get("event_type", pd.Series(index=frame.index, dtype=object)) == "off_ball_run"]
    top_run = off_ball.sort_values("distance_covered", ascending=False).head(1) if "distance_covered" in off_ball else pd.DataFrame()
    top_threat = frame.sort_values("xthreat", ascending=False).head(1) if "xthreat" in frame else pd.DataFrame()
    return {
        "events": int(len(frame)),
        "player_possessions": _event_count(frame, "player_possession"),
        "off_ball_runs": int(len(off_ball)),
        "passing_options": _event_count(frame, "passing_option"),
        "on_ball_engagements": _event_count(frame, "on_ball_engagement"),
        "dangerous_events": _bool_sum(frame, "dangerous"),
        "received_runs": _bool_sum(off_ball, "received"),
        "targeted_runs": _bool_sum(off_ball, "targeted"),
        "high_intensity_runs": int(_high_intensity_mask(off_ball).sum()) if not off_ball.empty else 0,
        "xthreat_total": _xthreat_sum(frame),
        "longest_run_meters": round(float(_numeric_column(top_run, "distance_covered", 0.0).iloc[0]), 2) if not top_run.empty else 0.0,
        "longest_run_player": str(top_run["player_name"].iloc[0]) if not top_run.empty and "player_name" in top_run else "",
        "top_xthreat_player": str(top_threat["player_name"].iloc[0]) if not top_threat.empty and "player_name" in top_threat else "",
    }


def build_team_and_match_summaries() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matches = load_matches()
    team_rows: list[dict[str, Any]] = []
    team_match_rows: list[dict[str, Any]] = []
    match_rows: list[dict[str, Any]] = []
    event_samples: list[pd.DataFrame] = []
    offball_rows: list[pd.DataFrame] = []
    phase_rows: list[pd.DataFrame] = []

    for match in matches:
        match_id = match["id"]
        label = _match_label(match)
        detail = load_match_detail(match_id)
        phases = to_numeric(load_phases(match_id))
        events = to_numeric(load_dynamic_events(match_id))
        tracking = tracking_status(match_id)

        if not phases.empty:
            phase = phases.copy()
            phase["match_label"] = label
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
            events = events.copy()
            events["match_label"] = label
            event_summary = _summarise_events(events)
            match_rows.append({
                "match_id": match_id,
                "match_label": label,
                "date_time": match["date_time"],
                "score": f'{detail.get("home_team_score", "")}-{detail.get("away_team_score", "")}',
                "home_team": match["home_team"]["short_name"],
                "away_team": match["away_team"]["short_name"],
                **event_summary,
                "tracking_status": tracking["status"],
                "tracking_bytes": tracking["bytes"],
            })

            available = [column for column in ["match_label", *EVENT_EXPORT_COLUMNS] if column in events]
            event_samples.append(events[available])

            off_ball = events.loc[events.get("event_type", pd.Series(index=events.index, dtype=object)) == "off_ball_run"].copy()
            if not off_ball.empty:
                off_ball["high_intensity"] = _high_intensity_mask(off_ball)
                available_obr = [column for column in OFFBALL_EXPORT_COLUMNS if column in off_ball]
                offball_rows.append(off_ball[available_obr])

            for (team_id, team_name), group in events.groupby(["team_id", "team_shortname"], dropna=False):
                if pd.isna(team_id):
                    continue
                summary = _summarise_events(group)
                team_match_rows.append({
                    "match_id": match_id,
                    "match_label": label,
                    "team_id": int(team_id),
                    "team_name": team_name,
                    **summary,
                })

    team_summary = pd.DataFrame(team_rows)
    if not team_summary.empty:
        team_summary = team_summary.groupby(["team_id", "team_name", "phase_type"], as_index=False)["phase_minutes"].sum()
        totals = team_summary.groupby("team_id")["phase_minutes"].transform("sum")
        team_summary["phase_share_pct"] = (team_summary["phase_minutes"] / totals.replace(0, np.nan) * 100).fillna(0).round(2)
    match_summary = pd.DataFrame(match_rows)
    team_match_summary = pd.DataFrame(team_match_rows)
    event_sample = pd.concat(event_samples, ignore_index=True) if event_samples else pd.DataFrame()
    offball_runs = pd.concat(offball_rows, ignore_index=True) if offball_rows else pd.DataFrame()
    phase_timeline = pd.concat(phase_rows, ignore_index=True) if phase_rows else pd.DataFrame()
    return team_summary, match_summary, event_sample, offball_runs, team_match_summary, phase_timeline


def write_outputs() -> dict[str, Any]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    profiles = build_player_profiles()
    team_summary, match_summary, event_sample, offball_runs, team_match_summary, phase_timeline = build_team_and_match_summaries()

    profiles.to_csv(PLAYER_PROFILES_CSV, index=False)
    team_summary.to_csv(TEAM_SUMMARY_CSV, index=False)
    match_summary.to_csv(MATCH_SUMMARY_CSV, index=False)
    event_sample.to_csv(EVENT_SAMPLE_CSV, index=False)
    offball_runs.to_csv(OFFBALL_RUNS_CSV, index=False)
    team_match_summary.to_csv(MATCH_TEAM_SUMMARY_CSV, index=False)
    phase_timeline.to_csv(PHASE_TIMELINE_CSV, index=False)

    summary = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "source": "SkillCorner Open Data, AUS A-League 2024/2025",
        "rows": {
            "players": int(len(profiles)),
            "teams": int(team_summary["team_id"].nunique()) if not team_summary.empty else 0,
            "matches": int(len(match_summary)),
            "eventSample": int(len(event_sample)),
            "offBallRuns": int(len(offball_runs)),
            "teamMatchInsights": int(len(team_match_summary)),
            "phaseRows": int(len(phase_timeline)),
        },
        "metricGlossary": METRIC_GLOSSARY,
        "archetypeDefinitions": ARCHETYPE_DEFINITIONS,
        "displayLabels": {
            "events": EVENT_TYPE_LABELS,
            "phases": IN_POSSESSION_PHASE_LABELS,
            "tracking": TRACKING_STATUS_LABELS,
        },
        "topPlayers": profiles.head(10)[[
            "player_name", "team_name", "position_group", "profile_score", "archetype",
            "athletic_load_score", "off_ball_threat_score", "passing_progression_score",
        ]].to_dict("records"),
        "tracking": match_summary[["match_id", "match_label", "tracking_status", "tracking_bytes"]].to_dict("records") if not match_summary.empty else [],
    }
    ANALYSIS_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
