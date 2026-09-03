import pandas as pd

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
