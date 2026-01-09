from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_skill import CandidateSkill
from app.models.job_skill import JobSkill
from app.models.skill import Skill


if TYPE_CHECKING:
    pass


class MatchEngine:
    """AI Match Scoring Engine for candidate-job compatibility."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_match_score(
        self, candidate_id: uuid.UUID, job_id: uuid.UUID
    ) -> tuple[float, dict]:
        """
        Calculate compatibility score between candidate and job.
        
        Returns:
            (score, explanation) where score is 0-100 and explanation is structured JSON
        """
        job_skills_data = await self._get_job_skills(job_id)
        candidate_skills_data = await self._get_candidate_skills(candidate_id)

        if not job_skills_data:
            return 0.0, {
                "strategy": "skill_overlap_weighted_v1",
                "reason": "Job has no required skills",
                "matched_skills": [],
                "missing_skills": [],
                "weighted_contribution": 0.0,
                "experience_bonus": 0.0,
                "final_score": 0.0,
            }

        matched_skills = []
        missing_skills = []
        total_weight = 0.0
        matched_weight = 0.0
        experience_bonus = 0.0

        candidate_skill_map = {
            cs["skill_id"]: cs for cs in candidate_skills_data
        }

        for job_skill in job_skills_data:
            skill_id = job_skill["skill_id"]
            skill_name = job_skill["skill_name"]
            weight = job_skill["weight"] if job_skill["weight"] is not None else 1.0
            
            if weight < 0:
                weight = 0.0
            
            total_weight += weight

            if skill_id in candidate_skill_map:
                cs = candidate_skill_map[skill_id]
                matched_weight += weight
                
                years_exp = cs.get("years_experience", 0.0) or 0.0
                exp_bonus = min(years_exp * 2.0, 10.0)
                experience_bonus += exp_bonus

                matched_skills.append({
                    "skill_id": str(skill_id),
                    "skill_name": skill_name,
                    "weight": weight,
                    "level": cs.get("level"),
                    "years_experience": years_exp,
                    "experience_bonus": exp_bonus,
                })
            else:
                missing_skills.append({
                    "skill_id": str(skill_id),
                    "skill_name": skill_name,
                    "weight": weight,
                    "penalty": weight * 5.0,
                })

        base_score = (matched_weight / total_weight * 100.0) if total_weight > 0 else 0.0
        
        missing_penalty = sum(ms["penalty"] for ms in missing_skills)
        
        final_score = base_score + experience_bonus - missing_penalty
        
        final_score = max(0.0, min(100.0, final_score))

        explanation = {
            "strategy": "skill_overlap_weighted_v1",
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "weighted_contribution": round(base_score, 2),
            "experience_bonus": round(experience_bonus, 2),
            "missing_penalty": round(missing_penalty, 2),
            "final_score": round(final_score, 2),
            "total_job_skills": len(job_skills_data),
            "total_matched": len(matched_skills),
            "total_missing": len(missing_skills),
        }

        return final_score, explanation

    async def _get_job_skills(self, job_id: uuid.UUID) -> list[dict]:
        """Fetch job skills with weights."""
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
        """Fetch candidate skills with experience data."""
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
