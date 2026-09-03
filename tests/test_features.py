import pandas as pd

from skillcorner_intelligence.analytics import consolidate_player_aggregate
from skillcorner_intelligence.features import add_composite_scores, add_metric_derivatives, add_zscore_composite_scores, assign_archetypes, percentile_by_position, zscore_by_position


def test_position_percentiles_are_grouped() -> None:
    frame = pd.DataFrame({"position_group": ["A", "A", "B", "B"], "metric": [1, 3, 10, 20]})
    values = percentile_by_position(frame, "metric").tolist()
    assert values == [50.0, 100.0, 50.0, 100.0]


def test_zscore_constant_group_is_zero() -> None:
    frame = pd.DataFrame({"position_group": ["A", "A"], "metric": [5, 5]})
    assert zscore_by_position(frame, "metric").tolist() == [0.0, 0.0]


def test_composite_scores_stay_in_expected_range() -> None:
    frame = pd.DataFrame({
        "position_group": ["Forward", "Forward"],
        "minutes": [900, 90],
        "total_metersperminute_full_all": [120, 90],
        "running_distance_full_all": [1500, 700],
        "hsr_distance_full_all": [600, 100],
        "hi_count_full_all": [70, 20],
        "medaccel_count_full_all": [100, 40],
        "meddecel_count_full_all": [100, 40],
    })
    scored = assign_archetypes(add_composite_scores(frame))
    assert scored["profile_score"].between(0, 100).all()
    assert "archetype" in scored


def test_consolidate_player_aggregate_combines_context_rows() -> None:
    frame = pd.DataFrame({
        "player_id": [10, 10, 20],
        "player_name": ["A Player", "A Player", "B Player"],
        "player_short_name": ["A", "A", "B"],
        "player_birthdate": ["2000-01-01", "2000-01-01", "2001-01-01"],
        "team_id": [1, 1, 2],
        "team_name": ["One", "One", "Two"],
        "position_group": ["Midfield", "Wide Attacker", "Full Back"],
        "minutes_full_all": [90, 30, 90],
        "count_match": [2, 1, 1],
        "total_metersperminute_full_all": [100, 130, 80],
        "psv99": [30, 32, 28],
    })

    result = consolidate_player_aggregate(frame, "physical").sort_values("player_id")

    assert len(result) == 2
    first = result.loc[result["player_id"] == 10].iloc[0]
    assert first["minutes"] == 210
    assert first["count_match"] == 3
    assert first["position_group"] == "Midfield"
    assert first["position_groups"] == "Midfield; Wide Attacker"
    assert first["psv99"] == 32
    assert round(first["total_metersperminute_full_all"], 2) == 104.29


def test_zscore_composite_scores_center_on_position_average() -> None:
    frame = pd.DataFrame({
        "position_group": ["Midfield", "Midfield", "Midfield", "Full Back", "Full Back", "Full Back"],
        "minutes": [900, 900, 900, 900, 900, 900],
        "hi_count_full_all": [10, 20, 30, 5, 10, 15],
        "total_metersperminute_full_all": [80, 100, 120, 70, 80, 90],
        "hsr_distance_full_all": [100, 200, 300, 80, 100, 120],
        "psv99": [25, 30, 35, 24, 26, 28],
        "total_distance_full_all": [8000, 9000, 10000, 7000, 8000, 9000],
        "running_distance_full_all": [1000, 1300, 1600, 900, 1100, 1300],
        "hsr_count_full_all": [4, 8, 12, 3, 5, 7],
        "sprint_count_full_all": [1, 2, 3, 1, 2, 3],
    })
    metric_columns = [column for column in frame.columns if column not in {"position_group", "minutes"}]

    scored = add_zscore_composite_scores(add_metric_derivatives(frame, metric_columns))

    means = scored.groupby("position_group")["intensity_z_score"].mean().round(6).abs()
    assert means.eq(0).all()
    assert scored["intensity_z_score"].iloc[2] > scored["intensity_z_score"].iloc[0]
