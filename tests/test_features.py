import pandas as pd

from skillcorner_intelligence.analytics import consolidate_player_aggregate
from skillcorner_intelligence.features import add_composite_scores, assign_archetypes, percentile_by_position, zscore_by_position


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
