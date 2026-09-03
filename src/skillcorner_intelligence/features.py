from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

IDENTITY_COLUMNS = [
    "player_id",
    "player_name",
    "player_short_name",
    "player_birthdate",
    "team_id",
    "team_name",
    "position_group",
    "minutes",
]

METRIC_GLOSSARY = {
    "athletic_load_score": "Composite percentile for metres per minute, high-speed running, sprint volume, accelerations and decelerations.",
    "sprint_threat_score": "Composite percentile for high-intensity and sprint outputs, weighted toward repeat sprint actions.",
    "off_ball_threat_score": "Composite percentile for off-ball run volume, dangerous runs, penalty-area runs and targeted/received runs.",
    "passing_progression_score": "Composite percentile for line-breaking passes, pass-to-run completion, dangerous passes and xPass difficulty.",
    "in_possession_minutes": "Estimated time a player or team spent while their team had possession.",
    "out_of_possession_minutes": "Estimated time a player or team spent while their team defended.",
    "profile_score": "Blended analyst score combining athletic, off-ball and passing value with a playing-time reliability adjustment.",
}

COMPOSITE_INPUTS = {
    "athletic_load_score": [
        "total_metersperminute_full_all",
        "running_distance_full_all",
        "hsr_distance_full_all",
        "hi_count_full_all",
        "medaccel_count_full_all",
        "meddecel_count_full_all",
    ],
    "sprint_threat_score": [
        "hsr_distance_full_all",
        "hsr_count_full_all",
        "sprint_distance_full_all",
        "sprint_count_full_all",
        "explacceltosprint_count_full_all",
        "psv99",
    ],
    "off_ball_threat_score": [
        "offballrun_count_p30tip",
        "offballrun_count_dangerous_p30tip",
        "offballrun_count_penaltyarea_p30tip",
        "offballrun_count_targeted_p30tip",
        "offballrun_count_received_p30tip",
        "offballrun_count_shotwithin10s_p30tip",
    ],
    "passing_progression_score": [
        "pass_count_linebreak_completed_p30tip",
        "pass_count_torun_completed_p30tip",
        "pass_count_dangerous_completed_p30tip",
        "pass_count_difficultpass_attempted_p30tip",
        "pass_avgxpass_attempted",
        "pass_count_shotwithin10s_p30tip",
    ],
}


def as_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None, "None"):
        return default
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(value) or np.isinf(value):
        return default
    return value


def to_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if column not in {"player_name", "player_short_name", "player_birthdate", "team_name", "competition_name", "season_name", "position_group"}:
            converted = pd.to_numeric(result[column], errors="coerce")
            if converted.notna().any():
                result[column] = converted
    return result


def percentile_by_position(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    return frame.assign(_value=values).groupby("position_group")["_value"].rank(pct=True).fillna(0.0) * 100


def zscore_by_position(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)

    def normalize(series: pd.Series) -> pd.Series:
        std = series.std(ddof=0)
        if not std:
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - series.mean()) / std

    return values.groupby(frame["position_group"]).transform(normalize).fillna(0.0)


def add_metric_derivatives(frame: pd.DataFrame, source_columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in source_columns:
        if column in result:
            numeric = pd.to_numeric(result[column], errors="coerce").fillna(0.0)
            result[f"{column}_pctile"] = percentile_by_position(result.assign(**{column: numeric}), column).round(2)
            result[f"{column}_z"] = zscore_by_position(result.assign(**{column: numeric}), column).round(3)
    return result


def add_composite_scores(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for score, columns in COMPOSITE_INPUTS.items():
        available = [column for column in columns if column in result]
        if not available:
            result[score] = 0.0
            continue
        percentile_columns = []
        for column in available:
            pctile = f"{column}_pctile"
            if pctile not in result:
                result[pctile] = percentile_by_position(result, column).round(2)
            percentile_columns.append(pctile)
        result[score] = result[percentile_columns].mean(axis=1).round(2)

    minutes = pd.to_numeric(result.get("minutes", 0), errors="coerce").fillna(0.0)
    reliability = np.clip(minutes / 900.0, 0.35, 1.0)
    result["reliability_score"] = (reliability * 100).round(2)
    result["profile_score"] = (
        (
            0.28 * result["athletic_load_score"]
            + 0.24 * result["sprint_threat_score"]
            + 0.28 * result["off_ball_threat_score"]
            + 0.20 * result["passing_progression_score"]
        )
        * (0.80 + 0.20 * reliability)
    ).round(2)
    return result


def assign_archetypes(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    conditions = [
        (result["off_ball_threat_score"] >= 72) & (result["sprint_threat_score"] >= 65),
        (result["passing_progression_score"] >= 72) & (result["off_ball_threat_score"] >= 58),
        (result["athletic_load_score"] >= 72) & (result["passing_progression_score"] < 58),
        (result["passing_progression_score"] >= 72),
        (result["off_ball_threat_score"] >= 72),
    ]
    labels = [
        "Depth runner",
        "Connector creator",
        "High-output carrier",
        "Progression hub",
        "Box-movement threat",
    ]
    result["archetype"] = np.select(conditions, labels, default="Balanced contributor")
    return result
