from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics_engine import AnalyticsEngine
from app.crud.match import get_matches_by_candidate, get_matches_by_job, get_top_candidates


class InsightEngine:
    """Decision intelligence engine for recruiter and candidate insights."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics = AnalyticsEngine(db)

    async def generate_job_insights(self, job_id: uuid.UUID) -> list[dict]:
        """Generate insights for a specific job."""
        insights = []

        analytics = await self.analytics.compute_job_analytics(job_id)
        if not analytics:
            return insights

        insights.extend(await self._analyze_hiring_difficulty(job_id, analytics))
        insights.extend(await self._analyze_candidate_pool(job_id, analytics))
        insights.extend(await self._analyze_skill_scarcity(job_id, analytics))
        insights.extend(await self._analyze_top_candidates(job_id, analytics))

        return insights

    async def generate_candidate_insights(
        self, candidate_id: uuid.UUID
    ) -> list[dict]:
        """Generate insights for a specific candidate."""
        insights = []

        analytics = await self.analytics.compute_candidate_analytics(candidate_id)
        if not analytics:
            return insights

        insights.extend(
            await self._analyze_candidate_strengths(candidate_id, analytics)
        )
        insights.extend(await self._analyze_skill_gaps(candidate_id, analytics))
        insights.extend(await self._analyze_versatility(candidate_id, analytics))
        insights.extend(
            await self._analyze_improvement_opportunities(candidate_id, analytics)
        )

        return insights

    async def _analyze_hiring_difficulty(
        self, job_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Analyze hiring difficulty and generate insights."""
        insights = []
        difficulty = analytics["hiring_difficulty_score"]
        avg_score = analytics["average_match_score"]

        if difficulty >= 75:
            insights.append(
                {
                    "entity_type": "job",
                    "entity_id": job_id,
                    "insight_type": "hiring_risk",
                    "title": "High Hiring Difficulty Detected",
                    "description": f"This position has a hiring difficulty score of {difficulty:.0f}/100. "
                    f"The average candidate match score is {avg_score:.1f}%, indicating limited qualified candidates. "
                    f"Consider expanding skill requirements or offering competitive compensation.",
                    "severity": "high",
                    "confidence_score": 90.0,
                    "data": {
                        "difficulty_score": difficulty,
                        "avg_match_score": avg_score,
                        "threshold": 75,
                    },
                }
            )
        elif difficulty >= 50:
            insights.append(
                {
                    "entity_type": "job",
                    "entity_id": job_id,
                    "insight_type": "hiring_risk",
                    "title": "Moderate Hiring Challenge",
                    "description": f"This position has moderate hiring difficulty ({difficulty:.0f}/100). "
                    f"While candidates exist, the average match score is {avg_score:.1f}%. "
                    f"Review skill weight distribution to optimize candidate matching.",
                    "severity": "medium",
                    "confidence_score": 80.0,
                    "data": {
                        "difficulty_score": difficulty,
                        "avg_match_score": avg_score,
                        "threshold": 50,
                    },
                }
            )
        else:
            insights.append(
                {
                    "entity_type": "job",
                    "entity_id": job_id,
                    "insight_type": "hiring_opportunity",
                    "title": "Strong Candidate Pool Available",
                    "description": f"This position has low hiring difficulty ({difficulty:.0f}/100) "
                    f"with an average candidate match score of {avg_score:.1f}%. "
                    f"Multiple qualified candidates are available for interviews.",
                    "severity": "low",
                    "confidence_score": 85.0,
                    "data": {
                        "difficulty_score": difficulty,
                        "avg_match_score": avg_score,
                        "threshold": 50,
                    },
                }
            )

        return insights

    async def _analyze_candidate_pool(
        self, job_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Analyze candidate pool size."""
        insights = []
        candidate_count = analytics["candidate_count"]

        if candidate_count == 0:
            insights.append(
                {
                    "entity_type": "job",
                    "entity_id": job_id,
                    "insight_type": "hiring_risk",
                    "title": "No Candidate Matches Yet",
                    "description": "No candidates have been matched to this position. "
                    "Run auto-scoring for existing candidates or post the job to attract applicants.",
                    "severity": "high",
                    "confidence_score": 100.0,
                    "data": {"candidate_count": 0, "action": "run_auto_scoring"},
                }
            )
        elif candidate_count < 3:
            insights.append(
                {
                    "entity_type": "job",
                    "entity_id": job_id,
                    "insight_type": "hiring_risk",
                    "title": "Limited Candidate Pool",
                    "description": f"Only {candidate_count} candidate(s) matched to this position. "
                    f"Expanding the candidate search or adjusting requirements may improve hiring success.",
                    "severity": "medium",
                    "confidence_score": 90.0,
                    "data": {
                        "candidate_count": candidate_count,
                        "threshold": 3,
                    },
                }
            )

        return insights

    async def _analyze_skill_scarcity(
        self, job_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Analyze skill scarcity for job requirements."""
        insights = []

        skill_demand = await self.analytics.compute_skill_demand()
        scarce_skills = [s for s in skill_demand if s["scarcity_ratio"] > 2.0]

        if scarce_skills:
            skill_names = [s["skill_name"] for s in scarce_skills[:3]]
            insights.append(
                {
                    "entity_type": "job",
                    "entity_id": job_id,
                    "insight_type": "skill_gap",
                    "title": "High-Demand Skills Detected",
                    "description": f"Skills in high demand with low supply: {', '.join(skill_names)}. "
                    f"These skills have a scarcity ratio > 2.0, indicating limited candidate availability. "
                    f"Consider training programs or alternative skill combinations.",
                    "severity": "medium",
                    "confidence_score": 85.0,
                    "data": {
                        "scarce_skills": [
                            {"name": s["skill_name"], "ratio": s["scarcity_ratio"]}
                            for s in scarce_skills[:3]
                        ]
                    },
                }
            )

        return insights

    async def _analyze_top_candidates(
        self, job_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Analyze top candidates and provide recommendations."""
        insights = []
        top_score = analytics.get("top_candidate_score")

        if top_score and top_score >= 80:
            top_candidates = await get_top_candidates(self.db, job_id, limit=3)
            if top_candidates:
                insights.append(
                    {
                        "entity_type": "job",
                        "entity_id": job_id,
                        "insight_type": "recommendation",
                        "title": "Highly Qualified Candidates Available",
                        "description": f"Top candidate scored {top_score:.1f}%, indicating excellent job fit. "
                        f"{len(top_candidates)} candidate(s) scored above 80%. "
                        f"Recommend prioritizing these candidates for interviews.",
                        "severity": "low",
                        "confidence_score": 95.0,
                        "data": {
                            "top_score": top_score,
                            "top_candidate_count": len(top_candidates),
                            "threshold": 80,
                        },
                    }
                )

        return insights

    async def _analyze_candidate_strengths(
        self, candidate_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Analyze candidate strengths."""
        insights = []
        best_score = analytics.get("best_job_score")
        avg_score = analytics["average_score"]

        if best_score and best_score >= 85:
            insights.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "insight_type": "candidate_strength",
                    "title": "Exceptional Job Match Found",
                    "description": f"Candidate achieved {best_score:.1f}% match score for their top job. "
                    f"This indicates strong skill alignment and experience fit. "
                    f"Recommend expedited interview process for top matches.",
                    "severity": "low",
                    "confidence_score": 95.0,
                    "data": {
                        "best_score": best_score,
                        "avg_score": avg_score,
                        "threshold": 85,
                    },
                }
            )
        elif avg_score >= 65:
            insights.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "insight_type": "candidate_strength",
                    "title": "Solid Overall Profile",
                    "description": f"Candidate maintains {avg_score:.1f}% average match score across jobs. "
                    f"Demonstrates consistent skill quality and broad applicability.",
                    "severity": "low",
                    "confidence_score": 80.0,
                    "data": {"avg_score": avg_score, "threshold": 65},
                }
            )

        return insights

    async def _analyze_skill_gaps(
        self, candidate_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Analyze skill gaps."""
        insights = []
        skill_gap_count = analytics["skill_gap_count"]

        if skill_gap_count >= 5:
            insights.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "insight_type": "skill_gap",
                    "title": "Significant Skill Gaps Identified",
                    "description": f"Candidate is missing {skill_gap_count} skills required by matched jobs. "
                    f"Upskilling in these areas could significantly improve match scores and job opportunities.",
                    "severity": "high",
                    "confidence_score": 90.0,
                    "data": {
                        "skill_gap_count": skill_gap_count,
                        "threshold": 5,
                    },
                }
            )
        elif skill_gap_count >= 2:
            insights.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "insight_type": "skill_gap",
                    "title": "Minor Skill Gaps Detected",
                    "description": f"Candidate is missing {skill_gap_count} skills from target jobs. "
                    f"Targeted skill development could improve competitiveness.",
                    "severity": "medium",
                    "confidence_score": 85.0,
                    "data": {
                        "skill_gap_count": skill_gap_count,
                        "threshold": 2,
                    },
                }
            )

        return insights

    async def _analyze_versatility(
        self, candidate_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Analyze candidate versatility."""
        insights = []
        versatility = analytics["versatility_score"]
        matched_jobs = analytics["matched_job_count"]

        if versatility >= 5 and matched_jobs >= 5:
            insights.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "insight_type": "candidate_strength",
                    "title": "Highly Versatile Candidate",
                    "description": f"Candidate scored 60%+ on {versatility} different jobs out of {matched_jobs} total matches. "
                    f"Demonstrates strong adaptability and broad skill foundation.",
                    "severity": "low",
                    "confidence_score": 90.0,
                    "data": {
                        "versatility_score": versatility,
                        "matched_job_count": matched_jobs,
                        "threshold": 5,
                    },
                }
            )
        elif versatility == 0 and matched_jobs > 0:
            insights.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "insight_type": "improvement_tip",
                    "title": "Limited Job Match Success",
                    "description": f"Candidate has not scored above 60% on any of {matched_jobs} matched jobs. "
                    f"Focus on strengthening core skills or targeting more aligned positions.",
                    "severity": "medium",
                    "confidence_score": 85.0,
                    "data": {
                        "versatility_score": 0,
                        "matched_job_count": matched_jobs,
                    },
                }
            )

        return insights

    async def _analyze_improvement_opportunities(
        self, candidate_id: uuid.UUID, analytics: dict
    ) -> list[dict]:
        """Generate improvement recommendations."""
        insights = []
        avg_score = analytics["average_score"]
        skill_gap_count = analytics["skill_gap_count"]

        if avg_score < 50 and skill_gap_count > 0:
            insights.append(
                {
                    "entity_type": "candidate",
                    "entity_id": candidate_id,
                    "insight_type": "improvement_tip",
                    "title": "Skill Development Recommended",
                    "description": f"Average match score is {avg_score:.1f}% with {skill_gap_count} identified skill gaps. "
                    f"Prioritize acquiring high-demand skills to improve job match rates and competitiveness.",
                    "severity": "high",
                    "confidence_score": 88.0,
                    "data": {
                        "avg_score": avg_score,
                        "skill_gap_count": skill_gap_count,
                        "action": "skill_development",
                    },
                }
            )

        return insights
