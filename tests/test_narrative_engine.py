import uuid
from types import SimpleNamespace

import pytest

from app.models.recommendation import Recommendation
from app.services.narrative_engine import MockLLMProvider, NarrativeEngine


class CustomLLMProvider:
    async def generate(self, prompt: str) -> str:
        return "Custom provider narrative with score details."


def _job_recommendation(**overrides) -> Recommendation:
    defaults = {
        "id": uuid.uuid4(),
        "entity_type": "job",
        "entity_id": uuid.uuid4(),
        "recommended_entity_id": uuid.uuid4(),
        "recommendation_type": "candidate_for_job",
        "rank": 1,
        "score": 88.0,
        "confidence": 92.0,
        "explanation": {
            "base_match_score": 85.0,
            "skill_gap_count": 2,
            "skill_gap_penalty": 4.0,
            "difficulty_penalty": 3.0,
            "hiring_difficulty": 72.0,
            "final_score": 88.0,
        },
    }
    defaults.update(overrides)
    return Recommendation(**defaults)


def _candidate_recommendation(**overrides) -> Recommendation:
    defaults = {
        "id": uuid.uuid4(),
        "entity_type": "candidate",
        "entity_id": uuid.uuid4(),
        "recommended_entity_id": uuid.uuid4(),
        "recommendation_type": "job_for_candidate",
        "rank": 2,
        "score": 79.0,
        "confidence": 86.0,
        "explanation": {
            "base_match_score": 74.0,
            "versatility_score": 4,
            "versatility_bonus": 6.0,
            "strength_bonus": 5.0,
            "has_strength_insight": True,
            "final_score": 79.0,
        },
    }
    defaults.update(overrides)
    return Recommendation(**defaults)


@pytest.mark.asyncio
async def test_generate_narrative_uses_fallback_when_mock_llm_enabled() -> None:
    engine = NarrativeEngine(MockLLMProvider())
    recommendation = _job_recommendation()

    result = await engine.generate_narrative(recommendation, tone="professional")

    assert result["tone_used"] == "professional"
    assert "88.0%" in result["narrative_text"]
    assert "skill gap" in result["narrative_text"].lower()
    assert result["version"] == NarrativeEngine.VERSION
    assert len(result["summary_bullets"]) >= 3


@pytest.mark.asyncio
async def test_generate_narrative_uses_custom_provider_text() -> None:
    engine = NarrativeEngine(CustomLLMProvider())
    recommendation = _job_recommendation()

    result = await engine.generate_narrative(recommendation)

    assert result["narrative_text"] == "Custom provider narrative with score details."
    assert result["confidence"] == pytest.approx(92.0)


@pytest.mark.asyncio
async def test_generate_narrative_supports_technical_tone_metadata() -> None:
    engine = NarrativeEngine(MockLLMProvider())
    recommendation = _candidate_recommendation()

    result = await engine.generate_narrative(recommendation, tone="technical")

    assert result["tone_used"] == "technical"
    assert "79.0%" in result["narrative_text"]
    assert any("Versatility" in bullet for bullet in result["summary_bullets"])


@pytest.mark.asyncio
async def test_generate_narrative_can_omit_summary_bullets() -> None:
    engine = NarrativeEngine(MockLLMProvider())
    recommendation = _job_recommendation(explanation={"base_match_score": 90.0, "skill_gap_count": 0, "final_score": 90.0})

    result = await engine.generate_narrative(recommendation, include_bullets=False)

    assert result["summary_bullets"] == []


def test_extract_bullets_marks_high_hiring_difficulty() -> None:
    engine = NarrativeEngine()
    recommendation = _job_recommendation(
        explanation={
            "base_match_score": 70.0,
            "skill_gap_count": 0,
            "hiring_difficulty": 82.0,
            "final_score": 70.0,
        }
    )

    bullets = engine._extract_bullets(recommendation)

    assert any("High (82/100)" in bullet for bullet in bullets)
    assert bullets[-1] == "Confidence: 92%"


def test_fallback_narrative_for_candidate_without_versatility() -> None:
    engine = NarrativeEngine()
    recommendation = _candidate_recommendation(
        explanation={
            "base_match_score": 68.0,
            "versatility_score": 0,
            "final_score": 68.0,
        }
    )

    narrative = engine._generate_fallback_narrative(recommendation)

    assert "specialized focus" in narrative
    assert "68.0%" in narrative
