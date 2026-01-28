from __future__ import annotations

LEVEL_SCORES: dict[str, float] = {
    "junior": 40.0,
    "mid": 60.0,
    "intermediate": 60.0,
    "senior": 80.0,
    "expert": 90.0,
    "lead": 95.0,
}


def level_to_score(level: str | None) -> float:
    if not level:
        return 50.0
    return LEVEL_SCORES.get(level.strip().lower(), 50.0)


def hiring_difficulty_score(
    *,
    avg_match_score: float,
    candidates_with_matches: int,
    required_skills_count: int,
) -> float:
    difficulty_base = 100.0 - avg_match_score

    if candidates_with_matches < 5:
        difficulty_base += 20.0
    elif candidates_with_matches < 10:
        difficulty_base += 10.0

    if required_skills_count > 10:
        difficulty_base += 15.0
    elif required_skills_count > 5:
        difficulty_base += 7.0

    return min(round(difficulty_base, 2), 100.0)


def skill_scarcity_index(*, demand: int, supply: int) -> float:
    if supply > 0:
        return min((demand / supply) * 10.0, 100.0)
    return 100.0 if demand > 0 else 0.0


def candidate_market_competitiveness(
    match_scores: list[float],
) -> tuple[float, int]:
    if not match_scores:
        return 0.0, 0

    avg_match_score = sum(match_scores) / len(match_scores)
    top_matches = [score for score in match_scores if score >= 80.0]
    score = avg_match_score
    if len(top_matches) >= 5:
        score = min(score + 10.0, 100.0)
    return round(score, 2), len(top_matches)


def candidate_versatility_index(
    skill_levels: list[str | None],
) -> tuple[float, float, int]:
    skill_count = len(skill_levels)
    versatility_base = min(skill_count * 5.0, 80.0)

    high_proficiency = [level for level in skill_levels if level_to_score(level) >= 80.0]
    if len(high_proficiency) >= 3:
        versatility_base += 20.0
    elif len(high_proficiency) >= 1:
        versatility_base += 10.0

    avg_proficiency = (
        sum(level_to_score(level) for level in skill_levels) / len(skill_levels)
        if skill_levels
        else 0.0
    )
    return min(round(versatility_base, 2), 100.0), round(avg_proficiency, 2), len(high_proficiency)


def growth_potential_score(
    *,
    versatility_index: float,
    skill_depth_score: float,
    max_years_experience: float,
) -> float:
    growth_potential_base = (versatility_index * 0.5) + (skill_depth_score * 0.5)
    if max_years_experience < 5.0 and skill_depth_score >= 70.0:
        growth_potential_base = min(growth_potential_base + 15.0, 100.0)
    return round(growth_potential_base, 2)
