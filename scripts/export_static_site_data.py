from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skillcorner_intelligence.paths import ANALYSIS_JSON, MATCH_SUMMARY_CSV, PLAYER_PROFILES_CSV, STATIC_JSON, TEAM_SUMMARY_CSV

STREAMLIT_APP_URL = "https://skillcorner-app-m6j5idxghzigicecvxbchr.streamlit.app/?embed=true"


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    players = read_rows(PLAYER_PROFILES_CSV)
    teams = read_rows(TEAM_SUMMARY_CSV)
    matches = read_rows(MATCH_SUMMARY_CSV)
    analysis = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8")) if ANALYSIS_JSON.exists() else {}
    top_player_fields = [
        "player_name",
        "player_short_name",
        "team_name",
        "position_group",
        "archetype",
        "profile_score",
        "athletic_load_score",
        "off_ball_threat_score",
        "passing_progression_score",
    ]
    top_players = [
        {field: row.get(field, "") for field in top_player_fields}
        for row in sorted(players, key=lambda item: float(item.get("profile_score") or 0), reverse=True)[:30]
    ]
    payload = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "source": "SkillCorner Open Data: AUS A-League 2024/2025 aggregates, dynamic events and phases of play",
        "streamlitAppUrl": STREAMLIT_APP_URL,
        "scope": analysis.get("rows", {}),
        "metricGlossary": analysis.get("metricGlossary", {}),
        "topPlayers": top_players,
        "teamStyle": teams,
        "matches": matches,
    }
    STATIC_JSON.parent.mkdir(parents=True, exist_ok=True)
    STATIC_JSON.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {STATIC_JSON}")
