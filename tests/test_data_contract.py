import json
from pathlib import Path

from skillcorner_intelligence.paths import ANALYSIS_JSON, EVENT_SAMPLE_CSV, MATCH_SUMMARY_CSV, PLAYER_PROFILES_CSV, STATIC_JSON, TEAM_SUMMARY_CSV


def test_processed_outputs_exist_and_have_contract() -> None:
    assert PLAYER_PROFILES_CSV.exists()
    assert TEAM_SUMMARY_CSV.exists()
    assert MATCH_SUMMARY_CSV.exists()
    assert EVENT_SAMPLE_CSV.exists()
    players = PLAYER_PROFILES_CSV.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert {
        "player_id",
        "player_name",
        "team_name",
        "position_group",
        "profile_score",
        "athletic_load_score",
        "off_ball_threat_score",
        "passing_progression_score",
        "archetype",
    } <= set(players)


def test_analysis_summary_and_static_site_payload() -> None:
    summary = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    payload = json.loads(STATIC_JSON.read_text(encoding="utf-8"))
    assert summary["rows"]["players"] > 0
    assert summary["rows"]["matches"] == 10
    assert "profile_score" in summary["metricGlossary"]
    assert payload["topPlayers"]


def test_docs_front_door_references_static_payload_and_streamlit() -> None:
    index = Path("docs/index.html").read_text(encoding="utf-8")
    app = Path("docs/app.js").read_text(encoding="utf-8")
    assert "SkillCorner Football Intelligence Lab" in index
    assert "data/dashboard-data.json" in app
    assert "streamlit-frame" in index
