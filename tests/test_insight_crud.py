import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.insight import (
    auto_generate_insights_for_candidate,
    auto_generate_insights_for_job,
    create_insight,
    delete_insight,
    list_insights_by_entity,
)
from app.models.insight import Insight


@pytest.mark.asyncio
async def test_auto_generate_insights_for_job_replaces_existing_rows() -> None:
    job_id = uuid.uuid4()
    mock_db = AsyncMock()
    delete_result = MagicMock()
    delete_result.rowcount = 2
    mock_db.execute = AsyncMock(return_value=delete_result)

    generated = [
        {
            "entity_type": "job",
            "entity_id": job_id,
            "insight_type": "skill_gap",
            "title": "Missing Python depth",
            "description": "Few candidates meet the Python requirement.",
            "severity": "medium",
            "confidence_score": 0.82,
            "data": {},
        }
    ]

    created = Insight(
        id=uuid.uuid4(),
        entity_type="job",
        entity_id=job_id,
        insight_type="skill_gap",
        title="Missing Python depth",
        description="Few candidates meet the Python requirement.",
        severity="medium",
        confidence_score=0.82,
        data={},
    )

    with patch("app.crud.insight.InsightEngine") as mock_engine_cls, patch(
        "app.crud.insight.create_insight",
        new_callable=AsyncMock,
        return_value=created,
    ) as create_insight:
        mock_engine_cls.return_value.generate_job_insights = AsyncMock(return_value=generated)
        result = await auto_generate_insights_for_job(mock_db, job_id)

    assert len(result) == 1
    assert mock_db.execute.await_count == 1
    create_insight.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_generate_insights_for_candidate_persists_rows() -> None:
    candidate_id = uuid.uuid4()
    mock_db = AsyncMock()
    delete_result = MagicMock()
    delete_result.rowcount = 1
    mock_db.execute = AsyncMock(return_value=delete_result)

    generated = [
        {
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "insight_type": "skill_strength",
            "title": "Strong Python depth",
            "description": "Candidate exceeds role requirements.",
            "severity": "low",
            "confidence_score": 0.9,
            "data": {},
        }
    ]
    created = Insight(
        id=uuid.uuid4(),
        entity_type="candidate",
        entity_id=candidate_id,
        insight_type="skill_strength",
        title="Strong Python depth",
        description="Candidate exceeds role requirements.",
        severity="low",
        confidence_score=0.9,
        data={},
    )

    with patch("app.crud.insight.InsightEngine") as mock_engine_cls, patch(
        "app.crud.insight.create_insight",
        new_callable=AsyncMock,
        return_value=created,
    ) as create_insight_mock:
        mock_engine_cls.return_value.generate_candidate_insights = AsyncMock(return_value=generated)
        result = await auto_generate_insights_for_candidate(mock_db, candidate_id)

    assert len(result) == 1
    create_insight_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_list_and_delete_insight() -> None:
    entity_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    created = await create_insight(
        mock_db,
        entity_type="job",
        entity_id=entity_id,
        insight_type="pipeline",
        title="Slow pipeline",
        description="Few applicants this week.",
        severity="high",
        confidence_score=0.75,
        data={"week": 12},
    )

    assert created.entity_id == entity_id
    mock_db.add.assert_called_once()

    insight = Insight(
        id=uuid.uuid4(),
        entity_type="job",
        entity_id=entity_id,
        insight_type="pipeline",
        title="Slow pipeline",
        description="Few applicants this week.",
        severity="high",
        confidence_score=0.75,
        data={},
        created_at=datetime.now(timezone.utc),
    )
    list_lookup = MagicMock()
    list_lookup.scalars.return_value.all.return_value = [insight]
    mock_db.execute = AsyncMock(return_value=list_lookup)

    rows = await list_insights_by_entity(mock_db, "job", entity_id)

    assert len(rows) == 1
    assert rows[0].title == "Slow pipeline"

    delete_result = MagicMock()
    delete_result.rowcount = 1
    mock_db.execute = AsyncMock(return_value=delete_result)

    deleted = await delete_insight(mock_db, insight.id)

    assert deleted is True
