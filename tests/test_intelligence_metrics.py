from app.services.intelligence_metrics import (
    candidate_market_competitiveness,
    candidate_versatility_index,
    growth_potential_score,
    hiring_difficulty_score,
    level_to_score,
    skill_scarcity_index,
)


def test_level_to_score_maps_known_levels() -> None:
    assert level_to_score("senior") == 80.0
    assert level_to_score("unknown") == 50.0


def test_hiring_difficulty_increases_with_scarcity_and_complexity() -> None:
    easy = hiring_difficulty_score(
        avg_match_score=85.0,
        candidates_with_matches=20,
        required_skills_count=3,
    )
    hard = hiring_difficulty_score(
        avg_match_score=40.0,
        candidates_with_matches=2,
        required_skills_count=12,
    )
    assert hard > easy


def test_skill_scarcity_is_max_when_supply_is_zero() -> None:
    assert skill_scarcity_index(demand=5, supply=0) == 100.0
    assert skill_scarcity_index(demand=0, supply=0) == 0.0


def test_candidate_metrics_reward_top_matches() -> None:
    score, top_count = candidate_market_competitiveness([82, 84, 85, 90, 91, 60])
    assert top_count == 5
    assert score > 80.0


def test_growth_potential_bonus_for_early_career_depth() -> None:
    base = growth_potential_score(
        versatility_index=70.0,
        skill_depth_score=75.0,
        max_years_experience=8.0,
    )
    boosted = growth_potential_score(
        versatility_index=70.0,
        skill_depth_score=75.0,
        max_years_experience=3.0,
    )
    assert boosted > base


def test_versatility_rewards_breadth_and_senior_levels() -> None:
    narrow, depth, high_count = candidate_versatility_index(["junior"])
    broad, _, high_count_broad = candidate_versatility_index(
        ["senior", "expert", "lead", "mid", "junior"]
    )
    assert broad > narrow
    assert high_count_broad >= high_count
