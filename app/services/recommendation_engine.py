from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.match import get_matches_by_job, get_matches_by_candidate
from app.services.analytics_engine import AnalyticsEngine
from app.services.insight_engine import InsightEngine


class RecommendationEngine:
    """Deterministic recommendation engine for job-candidate matching."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics = AnalyticsEngine(db)
        self.insight_engine = InsightEngine(db)

    async def generate_job_recommendations(
        self, job_id: uuid.UUID, limit: int = 10
    ) -> list[dict]:
        """Generate ranked candidate recommendations for a job."""
        matches = await get_matches_by_job(self.db, job_id)
        if not matches:
            return []

        job_analytics = await self.analytics.compute_job_analytics(job_id)
        hiring_difficulty = (
            job_analytics.get("hiring_difficulty_score", 50) if job_analytics else 50
        )

        recommendations = []
        for match in matches:
            candidate_analytics = await self.analytics.compute_candidate_analytics(
                match.candidate_id
            )

            base_score = match.score
            experience_bonus = 0.0
            skill_gap_penalty = 0.0
            difficulty_penalty = 0.0

            if candidate_analytics:
                skill_gap_count = candidate_analytics.get("skill_gap_count", 0)
                skill_gap_penalty = min(skill_gap_count * 2.0, 15.0)

            if hiring_difficulty > 70:
                difficulty_penalty = (hiring_difficulty - 70) * 0.3

            final_score = max(
                0, min(100, base_score + experience_bonus - skill_gap_penalty - difficulty_penalty)
            )

            confidence = self._calculate_confidence(
                base_score, skill_gap_penalty, difficulty_penalty
            )

            recommendations.append(
                {
                    "entity_type": "job",
                    "entity_id": job_id,
                    "recommended_entity_id": match.candidate_id,
                    "recommendation_type": "candidate_for_job",
                    "score": final_score,
                    "confidence": confidence,
                    "explanation": {
                        "base_match_score": base_score,
                        "experience_bonus": experience_bonus,
                        "skill_gap_penalty": skill_gap_penalty,
                        "difficulty_penalty": difficulty_penalty,
                        "final_score": final_score,
                        "skill_gap_count": candidate_analytics.get("skill_gap_count", 0)
                        if candidate_analytics
                        else 0,
                        "hiring_difficulty": hiring_difficulty,
                    },
                }
            )

        recommendations.sort(key=lambda x: x["score"], reverse=True)

        for idx, rec in enumerate(recommendations[:limit], start=1):
            rec["rank"] = idx

        return recommendations[:limit]

    async def generate_candidate_recommendations(
        self, candidate_id: uuid.UUID, limit: int = 10
    ) -> list[dict]:
        """Generate ranked job recommendations for a candidate."""
        matches = await get_matches_by_candidate(self.db, candidate_id)
        if not matches:
            return []

        candidate_analytics = await self.analytics.compute_candidate_analytics(
            candidate_id
        )
        versatility_score = (
            candidate_analytics.get("versatility_score", 0) if candidate_analytics else 0
        )

        candidate_insights = await self.insight_engine.generate_candidate_insights(
            candidate_id
        )
        has_strength_insight = any(
            i.get("insight_type") == "candidate_strength" for i in candidate_insights
        )

        recommendations = []
        for match in matches:
            base_score = match.score
            versatility_bonus = min(versatility_score * 1.5, 10.0)
            strength_bonus = 5.0 if has_strength_insight else 0.0

            final_score = max(0, min(100, base_score + versatility_bonus + strength_bonus))

            confidence = self._calculate_candidate_confidence(
                base_score, versatility_score, has_strength_insight
            )

            recommendations.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "recommended_entity_id": match.job_id,
                    "recommendation_type": "job_for_candidate",
                    "score": final_score,
                    "confidence": confidence,
                    "explanation": {
                        "base_match_score": base_score,
                        "versatility_bonus": versatility_bonus,
                        "strength_bonus": strength_bonus,
                        "final_score": final_score,
                        "versatility_score": versatility_score,
                        "has_strength_insight": has_strength_insight,
                    },
                }
            )

        recommendations.sort(key=lambda x: x["score"], reverse=True)

        for idx, rec in enumerate(recommendations[:limit], start=1):
            rec["rank"] = idx

        return recommendations[:limit]

    def _calculate_confidence(
        self, base_score: float, skill_gap_penalty: float, difficulty_penalty: float
    ) -> float:
        """Calculate confidence score for job recommendations."""
        if base_score >= 85:
            confidence = 95.0
        elif base_score >= 70:
            confidence = 85.0
        elif base_score >= 60:
            confidence = 75.0
        else:
            confidence = 65.0

        if skill_gap_penalty > 10:
            confidence -= 10
        elif skill_gap_penalty > 5:
            confidence -= 5

        if difficulty_penalty > 5:
            confidence -= 5

        return max(50.0, min(100.0, confidence))

    def _calculate_candidate_confidence(
        self, base_score: float, versatility_score: int, has_strength: bool
    ) -> float:
        """Calculate confidence score for candidate recommendations."""
        if base_score >= 85:
            confidence = 95.0
        elif base_score >= 70:
            confidence = 85.0
        elif base_score >= 60:
            confidence = 75.0
        else:
            confidence = 65.0

        if versatility_score >= 5:
            confidence += 5
        if has_strength:
            confidence += 5

        return max(50.0, min(100.0, confidence))
