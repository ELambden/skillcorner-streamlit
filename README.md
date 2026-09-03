# SkillCorner Football Intelligence Lab

An analyst-facing Streamlit and GitHub Pages sample project built on [SkillCorner Open Data](https://github.com/SkillCorner/opendata).

The app turns the A-League 2024/2025 sample into scoutable player profiles, team phase summaries, and match-level dynamic-event views. It builds on SkillCorner's tutorial ideas, but moves from notebook examples into a reproducible hosted project.

## What It Shows

- Physical, off-ball run, and passing aggregates joined into one player profile table
- Position-group percentiles, z-scores, archetypes, and composite analyst scores
- Team phase-of-play summaries from the 10 sample matches
- Dynamic-event pitch maps for off-ball runs, passing options, possessions, dangerous actions, and xThreat
- Optional tracking-data detection for Git LFS JSONL files
- A static GitHub Pages front door that loads exported dashboard data and embeds the Streamlit app

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

Refresh the public data and processed artifacts:

```bash
python scripts/refresh_all.py
```

Run the app:

```bash
streamlit run app/streamlit_app.py
```

Preview the static site:

```bash
python -m http.server 8000 --directory docs
```

## Repository Guide

```text
app/                         Streamlit application
data/raw/                    Downloaded SkillCorner Open Data files, ignored by git
data/processed/              Committed analysis outputs used by Streamlit and docs
docs/                        Static GitHub Pages site
scripts/                     Fetch, feature build, export and refresh entry points
src/skillcorner_intelligence Reusable data, feature, analysis and visualization code
tests/                       Contract and scoring tests
```

## Tracking Data

The upstream tracking JSONL files are stored with Git LFS. A normal raw GitHub download returns small pointer files, so the project treats tracking as optional. The Streamlit app reports whether real tracking files are available and keeps the aggregate, phase, and event analysis fully usable without them.

## Data Credit

Data comes from SkillCorner Open Data, released in partnership with PySport. This project is an educational/portfolio sample and should credit SkillCorner when reused.

## GitHub Pages Deployment

The workflow in `.github/workflows/pages.yml` publishes the prebuilt `docs/` folder with GitHub Pages Actions. If the first run fails with `Get Pages site failed` or `Not Found`, enable Pages once in the repository UI:

1. Open `Settings` > `Pages` for `ELambden/skillcorner-streamlit`.
2. Under `Build and deployment`, set `Source` to `GitHub Actions`.
3. Rerun the `Deploy GitHub Pages` workflow.

For fully automated first-time enablement, create a repository secret named `PAGES_TOKEN` using a fine-grained token with Pages write access, then rerun the workflow. Without that secret, GitHub's default `GITHUB_TOKEN` can deploy once Pages is enabled, but it may not be allowed to create the Pages site on the first run.
