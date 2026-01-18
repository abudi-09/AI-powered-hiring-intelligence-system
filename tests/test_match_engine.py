import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.match_engine import MatchEngine


@pytest.mark.asyncio
async def test_match_score_is_zero_when_job_has_no_skills() -> None:
    engine = MatchEngine(db=AsyncMock())
    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()

    with patch.object(engine, "_get_job_skills", return_value=[]):
        with patch.object(
            engine,
            "_get_candidate_skills",
            return_value=[
                {
                    "skill_id": uuid.uuid4(),
                    "skill_name": "Python",
                    "level": "expert",
                    "years_experience": 5.0,
                }
            ],
        ):
            score, explanation = await engine.calculate_match_score(candidate_id, job_id)

    assert score == 0.0
    assert explanation["reason"] == "Job has no required skills"


@pytest.mark.asyncio
async def test_full_skill_match_caps_score_at_one_hundred() -> None:
    skill_id = uuid.uuid4()
    engine = MatchEngine(db=AsyncMock())
    job_skills = [{"skill_id": skill_id, "skill_name": "Python", "weight": 1.0}]
    candidate_skills = [
        {
            "skill_id": skill_id,
            "skill_name": "Python",
            "level": "senior",
            "years_experience": 2.0,
        }
    ]

    with patch.object(engine, "_get_job_skills", return_value=job_skills):
        with patch.object(engine, "_get_candidate_skills", return_value=candidate_skills):
            score, explanation = await engine.calculate_match_score(uuid.uuid4(), uuid.uuid4())

    assert score == pytest.approx(100.0)
    assert explanation["total_matched"] == 1
    assert explanation["total_missing"] == 0
