from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skillcorner_intelligence.paths import (
    ANALYSIS_JSON,
    MATCH_SUMMARY_CSV,
    MATCH_TEAM_SUMMARY_CSV,
    OFFBALL_RUNS_CSV,
    PLAYER_PROFILES_CSV,
    STATIC_JSON,
    TEAM_SUMMARY_CSV,
)
from skillcorner_intelligence.presentation import (
    ARCHETYPE_DEFINITIONS,
    EVENT_TYPE_LABELS,
    IN_POSSESSION_PHASE_LABELS,
    RUN_SUBTYPE_LABELS,
    SPEED_BAND_LABELS,
    TRACKING_STATUS_LABELS,
)

STREAMLIT_APP_URL = "https://skillcorner-app-m6j5idxghzigicecvxbchr.streamlit.app/?embed=true"


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def number(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


if __name__ == "__main__":
    players = read_rows(PLAYER_PROFILES_CSV)
    teams = read_rows(TEAM_SUMMARY_CSV)
    matches = read_rows(MATCH_SUMMARY_CSV)
    match_teams = read_rows(MATCH_TEAM_SUMMARY_CSV)
    offball_runs = read_rows(OFFBALL_RUNS_CSV)
    analysis = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8")) if ANALYSIS_JSON.exists() else {}
    top_player_fields = [
        "player_name",
        "player_short_name",
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
        "off_ball_threat_score",
        "passing_progression_score",
    ]
    top_players = [
        {field: row.get(field, "") for field in top_player_fields}
        for row in sorted(players, key=lambda item: number(item.get("profile_score")), reverse=True)[:30]
    ]
    top_runs = [
        {
            "match_label": row.get("match_label", ""),
            "player_name": row.get("player_name", ""),
            "team_shortname": row.get("team_shortname", ""),
            "event_subtype": row.get("event_subtype", ""),
            "speed_avg_band": row.get("speed_avg_band", ""),
            "distance_covered": row.get("distance_covered", ""),
            "xthreat": row.get("xthreat", ""),
            "dangerous": row.get("dangerous", ""),
            "received": row.get("received", ""),
        }
        for row in sorted(offball_runs, key=lambda item: (number(item.get("dangerous")), number(item.get("xthreat")), number(item.get("distance_covered"))), reverse=True)[:20]
    ]
    payload = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "source": "SkillCorner Open Data: AUS A-League 2024/2025 aggregates, dynamic events and phases of play",
        "streamlitAppUrl": STREAMLIT_APP_URL,
        "scope": analysis.get("rows", {}),
        "metricGlossary": analysis.get("metricGlossary", {}),
        "archetypeDefinitions": ARCHETYPE_DEFINITIONS,
        "displayLabels": {
            "events": EVENT_TYPE_LABELS,
            "phases": IN_POSSESSION_PHASE_LABELS,
            "tracking": TRACKING_STATUS_LABELS,
            "runSubtypes": RUN_SUBTYPE_LABELS,
            "speedBands": SPEED_BAND_LABELS,
        },
        "topPlayers": top_players,
        "teamStyle": teams,
        "matches": matches,
        "teamMatchInsights": match_teams,
        "topOffBallRuns": top_runs,
    }
    STATIC_JSON.parent.mkdir(parents=True, exist_ok=True)
    STATIC_JSON.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {STATIC_JSON}")
