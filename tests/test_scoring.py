import uuid

import pytest

from app.services.scoring import (
    CandidateSkillInput,
    JobSkillInput,
    calculate_weighted_match_score,
    level_multiplier,
    normalize_weight,
)


def test_normalize_weight_defaults_and_clamps() -> None:
    assert normalize_weight(None) == 1.0
    assert normalize_weight(-3.0) == 0.0


def test_match_score_zero_when_job_has_no_skills() -> None:
    score, explanation = calculate_weighted_match_score(
        [],
        [
            CandidateSkillInput(
                skill_id=str(uuid.uuid4()),
                skill_name="Python",
                level="senior",
                years_experience=5.0,
            )
        ],
    )
    assert score == 0.0
    assert explanation["reason"] == "Job has no required skills"


def test_full_skill_match_caps_at_one_hundred() -> None:
    skill_id = str(uuid.uuid4())
    score, explanation = calculate_weighted_match_score(
        [JobSkillInput(skill_id=skill_id, skill_name="Python", weight=1.0)],
        [
            CandidateSkillInput(
                skill_id=skill_id,
                skill_name="Python",
                level="senior",
                years_experience=2.0,
            )
        ],
    )
    assert score == pytest.approx(100.0)
    assert explanation["total_matched"] == 1


def test_missing_required_skill_applies_penalty() -> None:
    python_id = str(uuid.uuid4())
    react_id = str(uuid.uuid4())
    score, explanation = calculate_weighted_match_score(
        [
            JobSkillInput(skill_id=python_id, skill_name="Python", weight=1.0),
            JobSkillInput(skill_id=react_id, skill_name="React", weight=1.0),
        ],
        [
            CandidateSkillInput(
                skill_id=python_id,
                skill_name="Python",
                level="mid",
                years_experience=1.0,
            )
        ],
    )
    assert score < 100.0
    assert explanation["total_missing"] == 1
    assert explanation["missing_penalty"] == pytest.approx(5.0)


def test_senior_skill_level_increases_match_score() -> None:
    skill_id = str(uuid.uuid4())
    junior_score, _ = calculate_weighted_match_score(
        [JobSkillInput(skill_id=skill_id, skill_name="Python", weight=1.0)],
        [
            CandidateSkillInput(
                skill_id=skill_id,
                skill_name="Python",
                level="junior",
                years_experience=0.0,
            )
        ],
    )
    senior_score, senior_explanation = calculate_weighted_match_score(
        [JobSkillInput(skill_id=skill_id, skill_name="Python", weight=1.0)],
        [
            CandidateSkillInput(
                skill_id=skill_id,
                skill_name="Python",
                level="senior",
                years_experience=0.0,
            )
        ],
    )

    assert senior_score > junior_score
    assert senior_explanation["matched_skills"][0]["level_multiplier"] == pytest.approx(1.1)
    assert level_multiplier("senior") == pytest.approx(1.1)
