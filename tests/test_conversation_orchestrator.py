import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.analytics_engine import AnalyticsEngine
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.insight_engine import InsightEngine


@pytest.fixture
def job_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_execute_plan_returns_clarification_payload() -> None:
    orchestrator = ConversationOrchestrator(db=AsyncMock())
    plan = {
        "intent": "job_analysis",
        "steps": ["request_clarification"],
        "entities": {"entity_type": "job"},
    }

    result = await orchestrator.execute_plan(plan)

    assert "job ID or candidate ID" in result["message"]
    assert result["confidence"] == 100.0


@pytest.mark.asyncio
async def test_execute_plan_returns_help_payload() -> None:
    orchestrator = ConversationOrchestrator(db=AsyncMock())
    plan = {
        "intent": "general_help",
        "steps": ["generate_help_response"],
        "entities": {},
    }

    result = await orchestrator.execute_plan(plan)

    assert result["intent"] == "general_help"
    assert "recruiter assistant" in result["message"]
    assert "Recommendations" in result["bullets"]


@pytest.mark.asyncio
async def test_execute_plan_rejects_invalid_entity_uuid() -> None:
    orchestrator = ConversationOrchestrator(db=AsyncMock())
    plan = {
        "intent": "job_analysis",
        "steps": ["fetch_job_analytics"],
        "entities": {"entity_type": "job", "entity_id": "not-a-uuid"},
    }

    result = await orchestrator.execute_plan(plan)

    assert result["intent"] == "error"
    assert "Invalid UUID" in result["bullets"][0]


@pytest.mark.asyncio
async def test_execute_plan_runs_job_analysis_steps(job_id: uuid.UUID) -> None:
    job_analytics = {
        "average_match_score": 78.0,
        "candidate_count": 5,
        "hiring_difficulty_score": 62.0,
    }
    job_insights = [{"severity": "high", "insight_type": "hiring_risk", "title": "Risk"}]
    matches = [SimpleNamespace(score=91.0)]

    with patch.object(
        AnalyticsEngine,
        "compute_job_analytics",
        new_callable=AsyncMock,
        return_value=job_analytics,
    ):
        with patch.object(
            InsightEngine,
            "generate_job_insights",
            new_callable=AsyncMock,
            return_value=job_insights,
        ):
            with patch(
                "app.services.conversation_orchestrator.get_matches_by_job",
                new_callable=AsyncMock,
                return_value=matches,
            ):
                orchestrator = ConversationOrchestrator(db=AsyncMock())
                plan = {
                    "intent": "job_analysis",
                    "steps": [
                        "fetch_job_analytics",
                        "fetch_job_insights",
                        "fetch_job_matches",
                    ],
                    "entities": {"entity_type": "job", "entity_id": str(job_id)},
                }
                result = await orchestrator.execute_plan(plan)

    assert result["analytics"] == job_analytics
    assert result["insights"] == job_insights
    assert result["matches"] == matches


@pytest.mark.asyncio
async def test_compose_response_for_job_analysis() -> None:
    orchestrator = ConversationOrchestrator(db=AsyncMock())
    collected = {
        "intent": "job_analysis",
        "analytics": {
            "average_match_score": 81.5,
            "candidate_count": 6,
            "hiring_difficulty_score": 55.0,
        },
        "insights": [{"severity": "high", "insight_type": "hiring_risk", "title": "Risk"}],
    }

    response = await orchestrator.compose_response(collected, "Why is this job hard to hire for?")

    assert "81.5%" in response["message"]
    assert "high-priority insight" in response["message"]
    assert "analytics" in response["sources"]
    assert response["confidence"] >= 85.0


@pytest.mark.asyncio
async def test_compose_response_for_recommendation_request() -> None:
    orchestrator = ConversationOrchestrator(db=AsyncMock())
    top_rec = SimpleNamespace(rank=1, score=93.5, confidence=96.0)
    collected = {
        "intent": "recommendation_request",
        "recommendations": [top_rec, SimpleNamespace(rank=2, score=88.0, confidence=90.0)],
    }

    response = await orchestrator.compose_response(collected, "Who should I hire?")

    assert "93.5%" in response["message"]
    assert response["confidence"] == pytest.approx(96.0)
    assert "recommendations" in response["sources"]


@pytest.mark.asyncio
async def test_compose_response_prompts_for_more_context_when_empty() -> None:
    orchestrator = ConversationOrchestrator(db=AsyncMock())
    collected = {"intent": "match_explanation", "matches": []}

    response = await orchestrator.compose_response(collected, "Explain the match")

    assert "more context" in response["message"]
    assert response["confidence"] == 50.0
