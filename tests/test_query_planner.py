import uuid

from app.services.query_planner import QueryPlanner


def test_job_analysis_plan_includes_expected_steps() -> None:
    planner = QueryPlanner()
    entity_id = str(uuid.uuid4())

    plan = planner.plan(
        "job_analysis",
        {"entity_type": "job", "entity_id": entity_id},
    )

    assert plan["intent"] == "job_analysis"
    assert plan["steps"] == [
        "fetch_job_analytics",
        "fetch_job_insights",
        "fetch_job_matches",
    ]
    assert plan["requires_entity"] is True


def test_general_help_does_not_require_entity() -> None:
    planner = QueryPlanner()

    plan = planner.plan("general_help", {})

    assert plan["steps"] == ["generate_help_response"]
    assert plan["requires_entity"] is False


def test_missing_entity_requests_clarification() -> None:
    planner = QueryPlanner()

    plan = planner.plan("candidate_analysis", {"entity_type": "candidate"})

    assert plan["steps"] == ["request_clarification"]
    assert plan["requires_entity"] is True


def test_unknown_intent_falls_back_to_help_response() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        "unknown_intent",
        {"entity_type": "job", "entity_id": str(uuid.uuid4())},
    )

    assert plan["steps"] == ["generate_help_response"]


def test_skill_gap_analysis_plan() -> None:
    planner = QueryPlanner()

    plan = planner.plan(
        "skill_gap_analysis",
        {"entity_type": "job", "entity_id": str(uuid.uuid4())},
    )

    assert "fetch_skill_demand" in plan["steps"]
    assert plan["entities"]["entity_type"] == "job"
