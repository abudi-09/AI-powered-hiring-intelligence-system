"""Intelligence engine for dashboard analytics.

This module provides deterministic analytics for hiring intelligence:
- Job intelligence (hiring difficulty, candidate availability, skill scarcity)
- Candidate intelligence (market competitiveness, versatility, skill depth)
- Skill intelligence (demand/supply, scarcity ratio)
- Match intelligence (score distribution, quality index)
- Recruiter performance (acceptance rate, time to hire, success rate)

All calculations are deterministic and use only database data.
"""
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.candidate_skill import CandidateSkill
from app.models.job import Job
from app.models.job_skill import JobSkill
from app.models.match import MatchScore
from app.models.recommendation import Recommendation


class IntelligenceEngine:
    """Analytics engine for hiring intelligence metrics.
    
    All methods are deterministic and produce the same output for the same input.
    """

    VERSION = "1.0.0"

    @staticmethod
    async def calculate_job_intelligence(
        db: AsyncSession,
        job_id: UUID,
    ) -> dict[str, Any]:
        """Calculate job intelligence metrics.
        
        Args:
            db: Database session
            job_id: Job UUID
            
        Returns:
            Dictionary with intelligence metrics:
            - hiring_difficulty_score: 0-100 based on skill requirements and match scores
            - candidate_availability_ratio: candidates per required skill
            - skill_scarcity_index: 0-100 based on skill demand/supply
            - avg_match_score: average match score for this job
            - breakdown: detailed metrics
        """
        # Get job and its skills
        job_result = await db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Count required skills
        job_skills_result = await db.execute(
            select(func.count(JobSkill.skill_id))
            .where(JobSkill.job_id == job_id)
        )
        required_skills_count = job_skills_result.scalar() or 0

        # Get match scores for this job
        match_scores_result = await db.execute(
            select(MatchScore.score)
            .where(MatchScore.job_id == job_id)
            .order_by(MatchScore.score.desc())
        )
        match_scores = [row[0] for row in match_scores_result.all()]

        # Calculate avg match score
        avg_match_score = round(sum(match_scores) / len(match_scores), 2) if match_scores else 0.0

        # Count candidates with matches
        candidates_with_matches = len(match_scores)

        # Calculate candidate availability ratio
        if required_skills_count > 0:
            candidate_availability_ratio = round(candidates_with_matches / required_skills_count, 2)
        else:
            candidate_availability_ratio = 0.0

        # Calculate hiring difficulty score (inverse of match quality)
        # Higher difficulty if: low avg match score, few candidates, many required skills
        difficulty_base = 100 - avg_match_score  # Base difficulty from match scores

        # Adjust for candidate scarcity
        if candidates_with_matches < 5:
            difficulty_base += 20  # High difficulty if very few candidates
        elif candidates_with_matches < 10:
            difficulty_base += 10  # Medium difficulty if few candidates

        # Adjust for skill complexity
        if required_skills_count > 10:
            difficulty_base += 15  # High difficulty if many skills required
        elif required_skills_count > 5:
            difficulty_base += 7  # Medium difficulty if several skills required

        hiring_difficulty_score = min(round(difficulty_base, 2), 100.0)

        # Calculate skill scarcity index
        skill_scarcity_scores = []
        job_skills_data_result = await db.execute(
            select(JobSkill.skill_id)
            .where(JobSkill.job_id == job_id)
        )
        skill_ids = [row[0] for row in job_skills_data_result.all()]

        for skill_id in skill_ids:
            # Count jobs requiring this skill
            demand_result = await db.execute(
                select(func.count(JobSkill.job_id))
                .where(JobSkill.skill_id == skill_id)
            )
            demand = demand_result.scalar() or 0

            # Count candidates with this skill
            supply_result = await db.execute(
                select(func.count(CandidateSkill.candidate_id))
                .where(CandidateSkill.skill_id == skill_id)
            )
            supply = supply_result.scalar() or 0

            # Calculate scarcity (high demand, low supply = high scarcity)
            if supply > 0:
                scarcity = min((demand / supply) * 10, 100)  # Normalize to 0-100
            else:
                scarcity = 100  # Maximum scarcity if no supply

            skill_scarcity_scores.append(scarcity)

        skill_scarcity_index = round(
            sum(skill_scarcity_scores) / len(skill_scarcity_scores), 2
        ) if skill_scarcity_scores else 0.0

        # Build breakdown
        breakdown = {
            "required_skills_count": required_skills_count,
            "candidates_with_matches": candidates_with_matches,
            "match_score_range": {
                "min": round(min(match_scores), 2) if match_scores else 0.0,
                "max": round(max(match_scores), 2) if match_scores else 0.0,
                "median": round(match_scores[len(match_scores) // 2], 2) if match_scores else 0.0,
            },
            "difficulty_factors": {
                "low_match_quality": difficulty_base >= 60,
                "candidate_scarcity": candidates_with_matches < 10,
                "high_skill_complexity": required_skills_count > 5,
            },
        }

        return {
            "hiring_difficulty_score": hiring_difficulty_score,
            "candidate_availability_ratio": candidate_availability_ratio,
            "skill_scarcity_index": skill_scarcity_index,
            "avg_match_score": avg_match_score,
            "breakdown": breakdown,
        }

    @staticmethod
    async def calculate_candidate_intelligence(
        db: AsyncSession,
        candidate_id: UUID,
    ) -> dict[str, Any]:
        """Calculate candidate intelligence metrics.
        
        Args:
            db: Database session
            candidate_id: Candidate UUID
            
        Returns:
            Dictionary with intelligence metrics:
            - market_competitiveness_score: 0-100 based on match scores
            - versatility_index: 0-100 based on skill count and diversity
            - skill_depth_score: 0-100 based on skill proficiency levels
            - growth_potential_score: 0-100 based on versatility and depth
            - breakdown: detailed metrics
        """
        # Get candidate
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Get candidate skills
        skills_result = await db.execute(
            select(CandidateSkill.skill_id, CandidateSkill.proficiency_level)
            .where(CandidateSkill.candidate_id == candidate_id)
        )
        skills_data = skills_result.all()
        skill_count = len(skills_data)

        # Get match scores for this candidate
        match_scores_result = await db.execute(
            select(MatchScore.overall_score)
            .where(MatchScore.candidate_id == candidate_id)
            .order_by(MatchScore.overall_score.desc())
        )
        match_scores = [row[0] for row in match_scores_result.all()]

        # Calculate market competitiveness (based on match scores)
        avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0.0
        top_matches = [s for s in match_scores if s >= 80]
        
        market_competitiveness_score = avg_match_score
        if len(top_matches) >= 5:
            market_competitiveness_score = min(market_competitiveness_score + 10, 100)
        
        market_competitiveness_score = round(market_competitiveness_score, 2)

        # Calculate versatility index (skill count and diversity)
        # More skills = higher versatility, capped at 100
        versatility_base = min(skill_count * 5, 80)  # Max 80 from count
        
        # Bonus for high proficiency skills
        high_proficiency_skills = [s for s in skills_data if s[1] >= 80]
        if len(high_proficiency_skills) >= 3:
            versatility_base += 20
        elif len(high_proficiency_skills) >= 1:
            versatility_base += 10
        
        versatility_index = min(round(versatility_base, 2), 100.0)

        # Calculate skill depth score (average proficiency)
        avg_proficiency = sum([s[1] for s in skills_data]) / len(skills_data) if skills_data else 0.0
        skill_depth_score = round(avg_proficiency, 2)

        # Calculate growth potential (combination of versatility and depth)
        # High versatility + high depth = high growth potential
        growth_potential_base = (versatility_index * 0.5 + skill_depth_score * 0.5)
        
        # Bonus for young candidates with high skills
        if candidate.years_experience < 5 and skill_depth_score >= 70:
            growth_potential_base = min(growth_potential_base + 15, 100)
        
        growth_potential_score = round(growth_potential_base, 2)

        # Build breakdown
        breakdown = {
            "skill_count": skill_count,
            "match_count": len(match_scores),
            "top_match_count": len(top_matches),
            "avg_proficiency": round(avg_proficiency, 2),
            "high_proficiency_skills": len(high_proficiency_skills),
            "years_experience": candidate.years_experience,
            "strength_indicators": {
                "high_match_quality": avg_match_score >= 75,
                "skill_diversity": skill_count >= 5,
                "deep_expertise": skill_depth_score >= 80,
            },
        }

        return {
            "market_competitiveness_score": market_competitiveness_score,
            "versatility_index": versatility_index,
            "skill_depth_score": skill_depth_score,
            "growth_potential_score": growth_potential_score,
            "breakdown": breakdown,
        }

    @staticmethod
    async def calculate_skill_intelligence(
        db: AsyncSession,
        skill_id: UUID,
    ) -> dict[str, Any]:
        """Calculate skill intelligence metrics.
        
        Args:
            db: Database session
            skill_id: Skill UUID
            
        Returns:
            Dictionary with intelligence metrics:
            - demand_count: number of jobs requiring this skill
            - supply_count: number of candidates with this skill
            - scarcity_ratio: demand/supply ratio
            - avg_required_level: average required proficiency level
            - breakdown: detailed metrics
        """
        # Count jobs requiring this skill (demand)
        demand_result = await db.execute(
            select(func.count(JobSkill.job_id))
            .where(JobSkill.skill_id == skill_id)
        )
        demand_count = demand_result.scalar() or 0

        # Count candidates with this skill (supply)
        supply_result = await db.execute(
            select(func.count(CandidateSkill.candidate_id))
            .where(CandidateSkill.skill_id == skill_id)
        )
        supply_count = supply_result.scalar() or 0

        # Calculate scarcity ratio
        if supply_count > 0:
            scarcity_ratio = round(demand_count / supply_count, 2)
        else:
            scarcity_ratio = float(demand_count) if demand_count > 0 else 0.0

        # Get required levels for this skill in jobs
        # Use JobSkill.weight (0-1) as required level proxy (scale to 0-100)
        job_levels_result = await db.execute(
            select(JobSkill.weight)
            .where(JobSkill.skill_id == skill_id)
        )
        job_levels_raw = [row[0] for row in job_levels_result.all() if row[0] is not None]
        job_levels = [min(max(w * 100.0, 0.0), 100.0) for w in job_levels_raw]

        # Calculate average required level
        avg_required_level = round(
            sum(job_levels) / len(job_levels), 2
        ) if job_levels else 0.0

        # Get candidate proficiency levels
        # Use years_experience as candidate level proxy (scale years to 0-100)
        candidate_levels_result = await db.execute(
            select(CandidateSkill.years_experience)
            .where(CandidateSkill.skill_id == skill_id)
        )
        candidate_levels_raw = [row[0] for row in candidate_levels_result.all() if row[0] is not None]
        candidate_levels = [min(x * 10.0, 100.0) for x in candidate_levels_raw]

        avg_candidate_level = round(
            sum(candidate_levels) / len(candidate_levels), 2
        ) if candidate_levels else 0.0

        # Build breakdown
        breakdown = {
            "avg_required_level": avg_required_level,
            "avg_candidate_level": avg_candidate_level,
            "level_gap": round(avg_required_level - avg_candidate_level, 2) if candidate_levels else avg_required_level,
            "high_demand_jobs": len([l for l in job_levels if l >= 80]),
            "expert_candidates": len([l for l in candidate_levels if l >= 80]),
            "market_indicators": {
                "high_demand": demand_count >= 10,
                "low_supply": supply_count < 5,
                "skill_gap": avg_required_level > avg_candidate_level + 10 if candidate_levels else True,
            },
        }

        return {
            "demand_count": demand_count,
            "supply_count": supply_count,
            "scarcity_ratio": scarcity_ratio,
            "avg_required_level": avg_required_level,
            "breakdown": breakdown,
        }

    @staticmethod
    async def calculate_match_intelligence(
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Calculate overall match intelligence metrics.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with intelligence metrics:
            - score_distribution: histogram of match scores
            - top_percentile_score: 90th percentile match score
            - low_match_ratio: percentage of matches below 60
            - recommendation_quality_index: average recommendation score
            - breakdown: detailed metrics
        """
        # Get all match scores
        match_scores_result = await db.execute(
            select(MatchScore.score)
            .order_by(MatchScore.score.desc())
        )
        all_scores = [row[0] for row in match_scores_result.all()]

        if not all_scores:
            return {
                "score_distribution": {},
                "top_percentile_score": 0.0,
                "low_match_ratio": 0.0,
                "recommendation_quality_index": 0.0,
                "breakdown": {},
            }

        # Calculate score distribution (buckets: 0-20, 20-40, 40-60, 60-80, 80-100)
        distribution = {
            "0-20": len([s for s in all_scores if 0 <= s < 20]),
            "20-40": len([s for s in all_scores if 20 <= s < 40]),
            "40-60": len([s for s in all_scores if 40 <= s < 60]),
            "60-80": len([s for s in all_scores if 60 <= s < 80]),
            "80-100": len([s for s in all_scores if 80 <= s <= 100]),
        }

        # Calculate top percentile score (90th percentile)
        sorted_scores = sorted(all_scores, reverse=True)
        percentile_index = int(len(sorted_scores) * 0.1)  # Top 10%
        top_percentile_score = round(sorted_scores[percentile_index] if percentile_index < len(sorted_scores) else sorted_scores[-1], 2)

        # Calculate low match ratio (below 60)
        low_matches = len([s for s in all_scores if s < 60])
        low_match_ratio = round((low_matches / len(all_scores)) * 100, 2)

        # Get recommendation scores to calculate quality index
        recommendations_result = await db.execute(
            select(Recommendation.score)
        )
        recommendation_scores = [row[0] for row in recommendations_result.all()]

        avg_recommendation_score = round(
            sum(recommendation_scores) / len(recommendation_scores), 2
        ) if recommendation_scores else 0.0

        # Recommendation quality index (based on avg score and consistency)
        recommendation_quality_index = avg_recommendation_score

        # Build breakdown
        breakdown = {
            "total_matches": len(all_scores),
            "total_recommendations": len(recommendation_scores),
            "avg_match_score": round(sum(all_scores) / len(all_scores), 2),
            "avg_recommendation_score": avg_recommendation_score,
            "excellent_matches": distribution["80-100"],
            "good_matches": distribution["60-80"],
            "poor_matches": distribution["0-20"] + distribution["20-40"],
            "quality_indicators": {
                "high_quality_matching": top_percentile_score >= 85,
                "low_poor_matches": low_match_ratio < 20,
                "strong_recommendations": avg_recommendation_score >= 75,
            },
        }

        return {
            "score_distribution": distribution,
            "top_percentile_score": top_percentile_score,
            "low_match_ratio": low_match_ratio,
            "recommendation_quality_index": recommendation_quality_index,
            "breakdown": breakdown,
        }

    @staticmethod
    async def calculate_recruiter_performance(
        db: AsyncSession,
        recruiter_id: UUID,
    ) -> dict[str, Any]:
        """Calculate recruiter performance metrics.
        
        Args:
            db: Database session
            recruiter_id: Recruiter (user) UUID
            
        Returns:
            Dictionary with performance metrics:
            - recommendation_acceptance_rate: percentage of accepted recommendations
            - avg_time_to_hire: average days from job post to hire (simulated)
            - hire_success_rate: percentage of successful hires (simulated)
            - breakdown: detailed metrics
        """
        # Count jobs created by this recruiter
        jobs_result = await db.execute(
            select(func.count(Job.id))
            .where(Job.owner_id == recruiter_id)
        )
        total_jobs = jobs_result.scalar() or 0

        # Get job IDs for this recruiter
        job_ids_result = await db.execute(
            select(Job.id)
            .where(Job.owner_id == recruiter_id)
        )
        job_ids = [row[0] for row in job_ids_result.all()]

        # Count recommendations for these jobs
        if job_ids:
            recommendations_result = await db.execute(
                select(func.count(Recommendation.id))
                .where(
                    Recommendation.entity_type == "job",
                    Recommendation.entity_id.in_(job_ids)
                )
            )
            total_recommendations = recommendations_result.scalar() or 0

            # Get recommendation scores to estimate acceptance
            rec_scores_result = await db.execute(
                select(Recommendation.score)
                .where(
                    Recommendation.entity_type == "job",
                    Recommendation.entity_id.in_(job_ids)
                )
            )
            rec_scores = [row[0] for row in rec_scores_result.all()]

            # Simulate acceptance rate based on recommendation quality
            # High score recommendations more likely to be accepted
            high_quality_recs = len([s for s in rec_scores if s >= 80])
            medium_quality_recs = len([s for s in rec_scores if 60 <= s < 80])
            
            # Estimated acceptance: 80% for high quality, 50% for medium, 20% for low
            estimated_acceptances = (
                high_quality_recs * 0.8 +
                medium_quality_recs * 0.5 +
                (len(rec_scores) - high_quality_recs - medium_quality_recs) * 0.2
            )
            
            recommendation_acceptance_rate = round(
                (estimated_acceptances / len(rec_scores)) * 100, 2
            ) if rec_scores else 0.0
        else:
            total_recommendations = 0
            recommendation_acceptance_rate = 0.0
            rec_scores = []

        # Simulate avg time to hire (based on job difficulty)
        # In real system, this would be calculated from actual hire dates
        time_to_hire_days = []
        for job_id in job_ids:
            # Get job difficulty from match scores
            match_result = await db.execute(
                select(func.avg(MatchScore.overall_score))
                .where(MatchScore.job_id == job_id)
            )
            avg_match = match_result.scalar() or 50

            # Lower match scores = harder to hire = more time
            # Base: 30 days, +1 day per point below 70
            if avg_match < 70:
                days = 30 + (70 - avg_match)
            else:
                days = 30 - (avg_match - 70) * 0.3  # Faster if good matches
            
            time_to_hire_days.append(max(days, 7))  # Minimum 7 days

        avg_time_to_hire = round(
            sum(time_to_hire_days) / len(time_to_hire_days), 2
        ) if time_to_hire_days else 0.0

        # Simulate hire success rate (based on recommendation quality)
        # In real system, this would track actual successful hires
        if rec_scores:
            avg_rec_score = sum(rec_scores) / len(rec_scores)
            # Higher recommendation quality = higher success rate
            hire_success_rate = min(round(avg_rec_score * 0.9, 2), 100.0)
        else:
            hire_success_rate = 0.0

        # Build breakdown
        breakdown = {
            "total_jobs_posted": total_jobs,
            "total_recommendations_made": total_recommendations,
            "avg_recommendations_per_job": round(total_recommendations / total_jobs, 2) if total_jobs > 0 else 0.0,
            "high_quality_recommendations": len([s for s in rec_scores if s >= 80]),
            "performance_indicators": {
                "high_acceptance_rate": recommendation_acceptance_rate >= 70,
                "fast_time_to_hire": avg_time_to_hire <= 30,
                "high_success_rate": hire_success_rate >= 80,
            },
        }

        return {
            "recommendation_acceptance_rate": recommendation_acceptance_rate,
            "avg_time_to_hire": avg_time_to_hire,
            "hire_success_rate": hire_success_rate,
            "breakdown": breakdown,
        }
