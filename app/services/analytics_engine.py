from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.candidate_skill import CandidateSkill
from app.models.job import Job
from app.models.job_skill import JobSkill
from app.models.match import MatchScore
from app.models.skill import Skill


class AnalyticsEngine:
    """Analytics computation engine for recruiter intelligence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_job_analytics(self, job_id: uuid.UUID) -> dict:
        """Compute analytics for a specific job."""
        job_result = await self.db.execute(
            select(Job.title).where(Job.id == job_id)
        )
        job_row = job_result.one_or_none()
        if not job_row:
            return None

        job_title = job_row[0]

        match_stats = await self.db.execute(
            select(
                func.avg(MatchScore.score),
                func.count(MatchScore.id),
                func.max(MatchScore.score),
            ).where(MatchScore.job_id == job_id)
        )
        avg_score, candidate_count, top_score = match_stats.one()

        avg_score = float(avg_score) if avg_score is not None else 0.0
        candidate_count = int(candidate_count) if candidate_count is not None else 0
        top_score = float(top_score) if top_score is not None else None

        skill_count_result = await self.db.execute(
            select(func.count(JobSkill.skill_id)).where(JobSkill.job_id == job_id)
        )
        skill_count = skill_count_result.scalar() or 0

        skill_scarcity = await self._compute_skill_scarcity_for_job(job_id)

        hiring_difficulty = self._calculate_hiring_difficulty(
            avg_score, skill_scarcity, candidate_count
        )

        return {
            "job_id": job_id,
            "job_title": job_title,
            "average_match_score": round(avg_score, 2),
            "candidate_count": candidate_count,
            "hiring_difficulty_score": round(hiring_difficulty, 2),
            "top_candidate_score": round(top_score, 2) if top_score else None,
            "skill_count": skill_count,
        }

    async def compute_candidate_analytics(self, candidate_id: uuid.UUID) -> dict:
        """Compute analytics for a specific candidate."""
        candidate_result = await self.db.execute(
            select(Candidate.full_name).where(Candidate.id == candidate_id)
        )
        candidate_row = candidate_result.one_or_none()
        if not candidate_row:
            return None

        candidate_name = candidate_row[0]

        match_stats = await self.db.execute(
            select(
                func.max(MatchScore.score),
                func.avg(MatchScore.score),
                func.count(MatchScore.id),
            ).where(MatchScore.candidate_id == candidate_id)
        )
        best_score, avg_score, job_count = match_stats.one()

        best_score = float(best_score) if best_score is not None else None
        avg_score = float(avg_score) if avg_score is not None else 0.0
        job_count = int(job_count) if job_count is not None else 0

        versatility_result = await self.db.execute(
            select(func.count(MatchScore.id))
            .where(MatchScore.candidate_id == candidate_id)
            .where(MatchScore.score >= 60.0)
        )
        versatility_score = versatility_result.scalar() or 0

        skill_gap_count = await self._compute_skill_gap_count(candidate_id)

        return {
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "best_job_score": round(best_score, 2) if best_score else None,
            "average_score": round(avg_score, 2),
            "versatility_score": versatility_score,
            "skill_gap_count": skill_gap_count,
            "matched_job_count": job_count,
        }

    async def compute_skill_demand(self) -> list[dict]:
        """Compute demand and supply for all skills."""
        demand_result = await self.db.execute(
            select(
                Skill.id,
                Skill.name,
                func.count(func.distinct(JobSkill.job_id)).label("demand_count"),
            )
            .outerjoin(JobSkill, JobSkill.skill_id == Skill.id)
            .group_by(Skill.id, Skill.name)
        )

        skill_demand_map = {}
        for skill_id, skill_name, demand_count in demand_result.all():
            skill_demand_map[skill_id] = {
                "skill_id": skill_id,
                "skill_name": skill_name,
                "demand_count": demand_count or 0,
                "supply_count": 0,
                "scarcity_ratio": 0.0,
            }

        supply_result = await self.db.execute(
            select(
                CandidateSkill.skill_id,
                func.count(func.distinct(CandidateSkill.candidate_id)).label(
                    "supply_count"
                ),
            ).group_by(CandidateSkill.skill_id)
        )

        for skill_id, supply_count in supply_result.all():
            if skill_id in skill_demand_map:
                skill_demand_map[skill_id]["supply_count"] = supply_count or 0

        for skill_data in skill_demand_map.values():
            demand = skill_data["demand_count"]
            supply = skill_data["supply_count"]
            if supply > 0:
                skill_data["scarcity_ratio"] = round(demand / supply, 2)
            else:
                skill_data["scarcity_ratio"] = float(demand) if demand > 0 else 0.0

        return sorted(
            skill_demand_map.values(),
            key=lambda x: x["scarcity_ratio"],
            reverse=True,
        )

    async def compute_skill_scarcity(self) -> list[dict]:
        """Compute skill scarcity (high demand, low supply)."""
        all_skills = await self.compute_skill_demand()
        return [s for s in all_skills if s["scarcity_ratio"] > 1.0]

    async def compute_match_distribution(self) -> dict:
        """Compute match score distribution across buckets."""
        all_matches = await self.db.execute(select(MatchScore.score))
        scores = [float(row[0]) for row in all_matches.all()]

        if not scores:
            return {
                "total_matches": 0,
                "buckets": [],
                "average_score": 0.0,
                "median_bucket": "No data",
            }

        total = len(scores)
        avg_score = sum(scores) / total

        buckets = [
            {"range_start": 0, "range_end": 20, "count": 0},
            {"range_start": 21, "range_end": 40, "count": 0},
            {"range_start": 41, "range_end": 60, "count": 0},
            {"range_start": 61, "range_end": 80, "count": 0},
            {"range_start": 81, "range_end": 100, "count": 0},
        ]

        for score in scores:
            if score <= 20:
                buckets[0]["count"] += 1
            elif score <= 40:
                buckets[1]["count"] += 1
            elif score <= 60:
                buckets[2]["count"] += 1
            elif score <= 80:
                buckets[3]["count"] += 1
            else:
                buckets[4]["count"] += 1

        for bucket in buckets:
            bucket["percentage"] = round((bucket["count"] / total) * 100, 2)

        sorted_scores = sorted(scores)
        median_score = sorted_scores[len(sorted_scores) // 2]
        median_bucket = self._get_bucket_label(median_score)

        return {
            "total_matches": total,
            "buckets": buckets,
            "average_score": round(avg_score, 2),
            "median_bucket": median_bucket,
        }

    async def _compute_skill_scarcity_for_job(self, job_id: uuid.UUID) -> float:
        """Compute average skill scarcity for a job."""
        job_skills_result = await self.db.execute(
            select(JobSkill.skill_id).where(JobSkill.job_id == job_id)
        )
        skill_ids = [row[0] for row in job_skills_result.all()]

        if not skill_ids:
            return 1.0

        scarcities = []
        for skill_id in skill_ids:
            demand_result = await self.db.execute(
                select(func.count(JobSkill.job_id)).where(
                    JobSkill.skill_id == skill_id
                )
            )
            demand = demand_result.scalar() or 0

            supply_result = await self.db.execute(
                select(func.count(CandidateSkill.candidate_id)).where(
                    CandidateSkill.skill_id == skill_id
                )
            )
            supply = supply_result.scalar() or 0

            if supply > 0:
                scarcities.append(demand / supply)
            else:
                scarcities.append(float(demand) if demand > 0 else 1.0)

        return sum(scarcities) / len(scarcities) if scarcities else 1.0

    async def _compute_skill_gap_count(self, candidate_id: uuid.UUID) -> int:
        """Count skills the candidate is missing from matched jobs."""
        matched_jobs_result = await self.db.execute(
            select(MatchScore.job_id).where(MatchScore.candidate_id == candidate_id)
        )
        job_ids = [row[0] for row in matched_jobs_result.all()]

        if not job_ids:
            return 0

        candidate_skills_result = await self.db.execute(
            select(CandidateSkill.skill_id).where(
                CandidateSkill.candidate_id == candidate_id
            )
        )
        candidate_skill_ids = {row[0] for row in candidate_skills_result.all()}

        all_required_skills_result = await self.db.execute(
            select(func.distinct(JobSkill.skill_id)).where(
                JobSkill.job_id.in_(job_ids)
            )
        )
        required_skill_ids = {row[0] for row in all_required_skills_result.all()}

        gap_count = len(required_skill_ids - candidate_skill_ids)
        return gap_count

    def _calculate_hiring_difficulty(
        self, avg_score: float, skill_scarcity: float, candidate_count: int
    ) -> float:
        """Calculate hiring difficulty score (0-100, higher = harder to hire)."""
        if candidate_count == 0:
            return 100.0

        score_difficulty = 100.0 - avg_score

        scarcity_difficulty = min(skill_scarcity * 20.0, 50.0)

        pool_difficulty = max(0, 30.0 - (candidate_count * 2))

        total_difficulty = score_difficulty + scarcity_difficulty + pool_difficulty

        return max(0.0, min(100.0, total_difficulty))

    def _get_bucket_label(self, score: float) -> str:
        """Get bucket label for a score."""
        if score <= 20:
            return "0-20"
        elif score <= 40:
            return "21-40"
        elif score <= 60:
            return "41-60"
        elif score <= 80:
            return "61-80"
        else:
            return "81-100"
