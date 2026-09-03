from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skillcorner_intelligence.data import fetch_open_data


if __name__ == "__main__":
    manifest = fetch_open_data()
    print(f"Fetched {len(manifest['downloads'])} public SkillCorner files")
