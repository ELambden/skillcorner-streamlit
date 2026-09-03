from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from .paths import AGGREGATES_DIR, MATCHES_DIR, MATCHES_JSON, RAW_DIR

OPEN_DATA_BASE = "https://raw.githubusercontent.com/SkillCorner/opendata/master"
AGGREGATE_FILES = {
    "physical": "aus1league_physicalaggregates_20242025.csv",
    "offball_runs": "aus1league_obraggregates_20242025.csv",
    "passing": "aus1league_passingaggregates_20242025.csv",
}


def fetch_bytes(url: str, timeout: int = 90) -> bytes:
    request = Request(url, headers={"User-Agent": "skillcorner-football-intelligence/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def write_url(url: str, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = fetch_bytes(url)
    destination.write_bytes(payload)
    return {"path": str(destination), "bytes": len(payload), "url": url}


def fetch_open_data(raw_dir: Path = RAW_DIR, include_tracking_pointer: bool = True) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    AGGREGATES_DIR.mkdir(parents=True, exist_ok=True)
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)

    downloads: list[dict[str, Any]] = []
    downloads.append(write_url(f"{OPEN_DATA_BASE}/data/matches.json", MATCHES_JSON))
    matches = json.loads(MATCHES_JSON.read_text(encoding="utf-8"))

    for filename in AGGREGATE_FILES.values():
        downloads.append(write_url(f"{OPEN_DATA_BASE}/data/aggregates/{filename}", AGGREGATES_DIR / filename))

    for match in matches:
        match_id = str(match["id"])
        match_dir = MATCHES_DIR / match_id
        for suffix in ["match.json", "dynamic_events.csv", "phases_of_play.csv"]:
            filename = f"{match_id}_{suffix}"
            downloads.append(write_url(f"{OPEN_DATA_BASE}/data/matches/{match_id}/{filename}", match_dir / filename))
        if include_tracking_pointer:
            filename = f"{match_id}_tracking_extrapolated.jsonl"
            try:
                downloads.append(write_url(f"{OPEN_DATA_BASE}/data/matches/{match_id}/{filename}", match_dir / filename))
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                downloads.append({"path": str(match_dir / filename), "bytes": 0, "error": str(exc)})

    manifest = {
        "fetchedAt": datetime.now(UTC).isoformat(),
        "source": "https://github.com/SkillCorner/opendata",
        "downloads": downloads,
    }
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_matches() -> list[dict[str, Any]]:
    return json.loads(MATCHES_JSON.read_text(encoding="utf-8"))


def load_match_detail(match_id: str | int) -> dict[str, Any]:
    path = MATCHES_DIR / str(match_id) / f"{match_id}_match.json"
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def load_aggregate(kind: str) -> pd.DataFrame:
    return read_csv(AGGREGATES_DIR / AGGREGATE_FILES[kind])


def load_dynamic_events(match_id: str | int) -> pd.DataFrame:
    return read_csv(MATCHES_DIR / str(match_id) / f"{match_id}_dynamic_events.csv")


def load_phases(match_id: str | int) -> pd.DataFrame:
    return read_csv(MATCHES_DIR / str(match_id) / f"{match_id}_phases_of_play.csv")


def tracking_status(match_id: str | int) -> dict[str, Any]:
    path = MATCHES_DIR / str(match_id) / f"{match_id}_tracking_extrapolated.jsonl"
    if not path.exists():
        return {"match_id": str(match_id), "available": False, "status": "missing", "bytes": 0}
    size = path.stat().st_size
    head = path.read_text(encoding="utf-8", errors="ignore")[:160]
    is_pointer = head.startswith("version https://git-lfs.github.com/spec/v1")
    return {
        "match_id": str(match_id),
        "available": size > 1024 and not is_pointer,
        "status": "available" if size > 1024 and not is_pointer else "lfs-pointer",
        "bytes": size,
    }


def load_tracking_frame(match_id: str | int) -> pd.DataFrame:
    """Load optional full tracking JSONL data when real Git LFS objects exist locally."""
    status = tracking_status(match_id)
    if not status["available"]:
        return pd.DataFrame()

    path = MATCHES_DIR / str(match_id) / f"{match_id}_tracking_extrapolated.jsonl"
    frame = pd.read_json(path, lines=True)
    if frame.empty:
        return frame

    if "possession" in frame:
        possession = pd.json_normalize(frame["possession"]).add_prefix("possession_")
        frame = pd.concat([frame.drop(columns=["possession"]), possession], axis=1)
    if "ball_data" in frame:
        ball = pd.json_normalize(frame["ball_data"]).add_prefix("ball_")
        frame = pd.concat([frame.drop(columns=["ball_data"]), ball], axis=1)
    frame["match_id"] = int(match_id)
    return frame
