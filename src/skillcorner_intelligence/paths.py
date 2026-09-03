from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DOCS_DIR = ROOT / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"

MATCHES_JSON = RAW_DIR / "matches.json"
AGGREGATES_DIR = RAW_DIR / "aggregates"
MATCHES_DIR = RAW_DIR / "matches"

PLAYER_PROFILES_CSV = PROCESSED_DIR / "player_profiles.csv"
TEAM_SUMMARY_CSV = PROCESSED_DIR / "team_style_summary.csv"
MATCH_SUMMARY_CSV = PROCESSED_DIR / "match_intelligence_summary.csv"
EVENT_SAMPLE_CSV = PROCESSED_DIR / "event_pitch_sample.csv"
PHASE_TIMELINE_CSV = PROCESSED_DIR / "phase_timeline.csv"
ANALYSIS_JSON = PROCESSED_DIR / "analysis_summary.json"
STATIC_JSON = DOCS_DATA_DIR / "dashboard-data.json"
