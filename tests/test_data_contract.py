import json
from pathlib import Path

from skillcorner_intelligence.paths import (
    ANALYSIS_JSON,
    EVENT_SAMPLE_CSV,
    MATCH_SUMMARY_CSV,
    MATCH_TEAM_SUMMARY_CSV,
    OFFBALL_RUNS_CSV,
    PLAYER_PROFILES_CSV,
    STATIC_JSON,
    TEAM_SUMMARY_CSV,
)


def test_processed_outputs_exist_and_have_contract() -> None:
    assert PLAYER_PROFILES_CSV.exists()
    assert TEAM_SUMMARY_CSV.exists()
    assert MATCH_SUMMARY_CSV.exists()
    assert EVENT_SAMPLE_CSV.exists()
    assert OFFBALL_RUNS_CSV.exists()
    assert MATCH_TEAM_SUMMARY_CSV.exists()
    players = PLAYER_PROFILES_CSV.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert {
        "player_id",
        "player_name",
        "team_name",
        "teams_played",
        "position_group",
        "position_groups",
        "profile_context_count",
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
    assert payload["topOffBallRuns"]


def test_docs_front_door_references_static_payload_and_streamlit() -> None:
    index = Path("docs/index.html").read_text(encoding="utf-8")
    app = Path("docs/app.js").read_text(encoding="utf-8")
    assert "SkillCorner Football Intelligence Lab" in index
    assert "data/dashboard-data.json" in app
    assert "streamlit-frame" in index
    assert "run-grid" in index


def test_static_payload_exports_friendly_labels_and_archetypes() -> None:
    payload = json.loads(STATIC_JSON.read_text(encoding="utf-8"))
    assert payload["displayLabels"]["events"]["player_possession"] == "In-possession action"
    assert payload["displayLabels"]["events"]["off_ball_run"] == "Off-ball movement"
    assert payload["displayLabels"]["phases"]["build_up"] == "Build-up"
    assert "Depth runner" in payload["archetypeDefinitions"]
    assert "prioritised" in payload["archetypeDefinitions"]["Connector creator"]
    assert payload["displayLabels"]["events"]["on_ball_engagement"] == "Defensive pressure"
    assert payload["displayLabels"]["runSubtypes"]["behind"] == "Run in behind"


def test_player_profiles_are_consolidated_by_player_id() -> None:
    import pandas as pd

    players = pd.read_csv(PLAYER_PROFILES_CSV)
    assert len(players) == players["player_id"].nunique()
    assert int(players.duplicated("player_id").sum()) == 0
    assert players["profile_context_count"].ge(1).all()


def test_match_intelligence_exports_full_dynamic_event_views() -> None:
    import pandas as pd

    events = pd.read_csv(EVENT_SAMPLE_CSV)
    offball = pd.read_csv(OFFBALL_RUNS_CSV)
    team_matches = pd.read_csv(MATCH_TEAM_SUMMARY_CSV)
    assert len(events) > 6000
    assert {"on_ball_engagement", "off_ball_run", "passing_option", "player_possession"} <= set(events["event_type"].dropna())
    assert {"player_in_possession_x_start", "player_in_possession_y_start"} <= set(events.columns)
    assert {"event_subtype", "speed_avg_band", "distance_covered", "high_intensity"} <= set(offball.columns)
    assert {"high_intensity_runs", "xthreat_total", "longest_run_player"} <= set(team_matches.columns)
