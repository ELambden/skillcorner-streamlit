from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skillcorner_intelligence.analytics import write_outputs
from skillcorner_intelligence.data import fetch_open_data
from skillcorner_intelligence.paths import STATIC_JSON

import runpy


if __name__ == "__main__":
    fetch_open_data()
    write_outputs()
    runpy.run_path(str(ROOT / "scripts" / "export_static_site_data.py"), run_name="__main__")
    print(f"Refresh complete. Static payload: {STATIC_JSON}")
