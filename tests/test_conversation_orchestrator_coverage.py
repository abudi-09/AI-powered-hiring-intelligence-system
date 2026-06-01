import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.conversation_orchestrator import ConversationOrchestrator


@pytest.fixture
def orchestrator() -> ConversationOrchestrator:
    return ConversationOrchestrator(AsyncMock())


@pytest.mark.asyncio
async def test_execute_plan_clarification(orchestrator: ConversationOrchestrator) -> None:
    plan = {
        "intent": "job_analysis",
        "steps": ["request_clarification"],
        "entities": {},
    }
    result = await orchestrator.execute_plan(plan)
    assert "need more information" in result["message"].lower()


@pytest.mark.asyncio
async def test_execute_plan_help(orchestrator: ConversationOrchestrator) -> None:
    plan = {"intent": "general_help", "steps": ["generate_help_response"], "entities": {}}
    result = await orchestrator.execute_plan(plan)
    assert result["intent"] == "general_help"
    assert "recruiter assistant" in result["message"].lower()


@pytest.mark.asyncio
async def test_execute_plan_invalid_entity_id(orchestrator: ConversationOrchestrator) -> None:
    plan = {
        "intent": "job_analysis",
        "steps": ["fetch_job_analytics"],
        "entities": {"entity_id": "not-a-uuid", "entity_type": "job"},
    }
    result = await orchestrator.execute_plan(plan)
    assert result["intent"] == "error"


@pytest.mark.asyncio
async def test_execute_plan_runs_all_fetch_steps(orchestrator: ConversationOrchestrator) -> None:
    job_id = uuid.uuid4()
    match = SimpleNamespace(score=88.0)
    recommendation = SimpleNamespace(rank=1, score=90.0, confidence=85.0)

    with patch.object(
        orchestrator.analytics,
        "compute_job_analytics",
        new_callable=AsyncMock,
        return_value={"average_match_score": 70.0, "candidate_count": 3, "hiring_difficulty_score": 55.0},
    ), patch.object(
        orchestrator.insight_engine,
        "generate_job_insights",
        new_callable=AsyncMock,
        return_value=[{"severity": "high", "insight_type": "gap", "title": "Gap"}],
    ), patch(
        "app.services.conversation_orchestrator.get_matches_by_job",
        new_callable=AsyncMock,
        return_value=[match],
    ), patch(
        "app.services.conversation_orchestrator.list_recommendations",
        new_callable=AsyncMock,
        return_value=[recommendation],
    ), patch.object(
        orchestrator.analytics,
        "compute_skill_demand",
        new_callable=AsyncMock,
        return_value=[{"skill_name": "Python"}],
    ):
        plan = {
            "intent": "job_analysis",
            "steps": [
                "fetch_job_analytics",
                "fetch_analytics",
                "fetch_job_insights",
                "fetch_insights",
                "fetch_job_matches",
                "fetch_recommendations",
                "fetch_skill_demand",
            ],
            "entities": {"entity_id": str(job_id), "entity_type": "job"},
        }
        result = await orchestrator.execute_plan(plan)

    assert result["analytics"] is not None
    assert result["insights"] is not None
    assert result["matches"] == [match]
    assert result["recommendations"] == [recommendation]
    assert result["skill_demand"][0]["skill_name"] == "Python"


@pytest.mark.asyncio
async def test_execute_plan_candidate_steps(orchestrator: ConversationOrchestrator) -> None:
    candidate_id = uuid.uuid4()
    with patch.object(
        orchestrator.analytics,
        "compute_candidate_analytics",
        new_callable=AsyncMock,
        return_value={"average_score": 72.0, "matched_job_count": 2, "versatility_score": 1},
    ), patch.object(
        orchestrator.insight_engine,
        "generate_candidate_insights",
        new_callable=AsyncMock,
        return_value=[{"insight_type": "candidate_strength", "title": "Strong"}],
    ), patch(
        "app.services.conversation_orchestrator.get_matches_by_candidate",
        new_callable=AsyncMock,
        return_value=[SimpleNamespace(score=80.0)],
    ):
        plan = {
            "intent": "candidate_analysis",
            "steps": [
                "fetch_candidate_analytics",
                "fetch_candidate_insights",
                "fetch_candidate_matches",
            ],
            "entities": {"entity_id": str(candidate_id), "entity_type": "candidate"},
        }
        result = await orchestrator.execute_plan(plan)

    assert result["analytics"]["average_score"] == 72.0
    assert result["matches"][0].score == 80.0


@pytest.mark.asyncio
async def test_compose_response_job_analysis(orchestrator: ConversationOrchestrator) -> None:
    data = {
        "intent": "job_analysis",
        "analytics": {"average_match_score": 71.5, "candidate_count": 4, "hiring_difficulty_score": 62.0},
        "insights": [{"severity": "high"}],
    }
    response = await orchestrator.compose_response(data, "analyze job")
    assert "71.5" in response["message"]
    assert response["confidence"] >= 85.0
    assert "analytics" in response["sources"]


@pytest.mark.asyncio
async def test_compose_response_candidate_analysis(orchestrator: ConversationOrchestrator) -> None:
    data = {
        "intent": "candidate_analysis",
        "analytics": {"average_score": 68.0, "matched_job_count": 3, "versatility_score": 2},
        "insights": [{"insight_type": "candidate_strength"}],
    }
    response = await orchestrator.compose_response(data, "analyze candidate")
    assert "68.0" in response["message"]
    assert "Strengths" in " ".join(response["bullets"])


@pytest.mark.asyncio
async def test_compose_response_recommendation_and_empty_paths(
    orchestrator: ConversationOrchestrator,
) -> None:
    rec = SimpleNamespace(rank=1, score=91.0, confidence=88.0)
    with_rec = await orchestrator.compose_response(
        {"intent": "recommendation_request", "recommendations": [rec]},
        "recommend",
    )
    assert "91.0" in with_rec["message"]

    without_rec = await orchestrator.compose_response(
        {"intent": "recommendation_request", "recommendations": []},
        "recommend",
    )
    assert "No recommendations" in without_rec["message"]


@pytest.mark.asyncio
async def test_compose_response_insight_skill_gap_and_match(orchestrator: ConversationOrchestrator) -> None:
    insight_resp = await orchestrator.compose_response(
        {
            "intent": "insight_explanation",
            "insights": [{"title": "Gap", "severity": "high"}],
        },
        "explain",
    )
    assert "1 insight" in insight_resp["message"]

    empty_insight = await orchestrator.compose_response(
        {"intent": "insight_explanation", "insights": []},
        "explain",
    )
    assert "No insights" in empty_insight["message"]

    skill_gap = await orchestrator.compose_response(
        {"intent": "skill_gap_analysis", "analytics": {"skill_gap_count": 2}},
        "gaps",
    )
    assert "2 skill gap" in skill_gap["message"]

    skill_gap_missing = await orchestrator.compose_response(
        {"intent": "skill_gap_analysis", "analytics": {}},
        "gaps",
    )
    assert "requires candidate context" in skill_gap_missing["message"]

    match_resp = await orchestrator.compose_response(
        {"intent": "match_explanation", "matches": [SimpleNamespace(score=77.0)]},
        "match",
    )
    assert "77.0" in match_resp["message"]

    fallback = await orchestrator.compose_response({"intent": "unknown"}, "help me")
    assert "more context" in fallback["message"].lower()
