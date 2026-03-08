import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.insight import auto_generate_insights_for_job
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
