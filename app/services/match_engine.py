from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_skill import CandidateSkill
from app.models.job_skill import JobSkill
from app.models.skill import Skill
from app.services.scoring import (
    CandidateSkillInput,
    JobSkillInput,
    calculate_weighted_match_score,
)


class MatchEngine:
    """Weighted skill-overlap scoring for candidate-job compatibility."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_match_score(
        self, candidate_id: uuid.UUID, job_id: uuid.UUID
    ) -> tuple[float, dict]:
        job_skills_data = await self._get_job_skills(job_id)
        candidate_skills_data = await self._get_candidate_skills(candidate_id)

        job_skills = [
            JobSkillInput(
                skill_id=str(row["skill_id"]),
                skill_name=row["skill_name"],
                weight=row["weight"] if row["weight"] is not None else 1.0,
            )
            for row in job_skills_data
        ]
        candidate_skills = [
            CandidateSkillInput(
                skill_id=str(row["skill_id"]),
                skill_name=row["skill_name"],
                level=row.get("level"),
                years_experience=row.get("years_experience"),
            )
            for row in candidate_skills_data
        ]
        return calculate_weighted_match_score(job_skills, candidate_skills)

    async def _get_job_skills(self, job_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(
                JobSkill.skill_id,
                Skill.name,
                JobSkill.weight,
            )
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(JobSkill.job_id == job_id)
        )

        return [
            {
                "skill_id": row[0],
                "skill_name": row[1],
                "weight": row[2],
            }
            for row in result.all()
        ]

    async def _get_candidate_skills(self, candidate_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(
                CandidateSkill.skill_id,
                Skill.name,
                CandidateSkill.level,
                CandidateSkill.years_experience,
            )
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .where(CandidateSkill.candidate_id == candidate_id)
        )

        return [
            {
                "skill_id": row[0],
                "skill_name": row[1],
                "level": row[2],
                "years_experience": row[3],
            }
            for row in result.all()
        ]
