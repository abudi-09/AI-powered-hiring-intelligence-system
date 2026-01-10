"""Intelligence CRUD operations."""
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import (
    CandidateIntelligence,
    JobIntelligence,
    MatchIntelligence,
    RecruiterPerformance,
    SkillIntelligence,
)
from app.services.intelligence_engine import IntelligenceEngine


async def generate_job_intelligence(
    db: AsyncSession,
    job_id: UUID,
) -> JobIntelligence:
    """Generate job intelligence analytics.
    
    Deletes existing intelligence and creates new record.
    
    Args:
        db: Database session
        job_id: Job UUID
        
    Returns:
        JobIntelligence record
    """
    # Delete existing intelligence for this job
    await db.execute(
        delete(JobIntelligence).where(JobIntelligence.job_id == job_id)
    )

    # Calculate intelligence metrics
    metrics = await IntelligenceEngine.calculate_job_intelligence(db, job_id)

    # Create new intelligence record
    intelligence = JobIntelligence(
        job_id=job_id,
        hiring_difficulty_score=metrics["hiring_difficulty_score"],
        candidate_availability_ratio=metrics["candidate_availability_ratio"],
        skill_scarcity_index=metrics["skill_scarcity_index"],
        avg_match_score=metrics["avg_match_score"],
        breakdown=metrics["breakdown"],
    )

    db.add(intelligence)
    await db.commit()
    await db.refresh(intelligence)

    return intelligence


async def get_job_intelligence(
    db: AsyncSession,
    job_id: UUID,
) -> JobIntelligence | None:
    """Get job intelligence by job ID.
    
    Args:
        db: Database session
        job_id: Job UUID
        
    Returns:
        JobIntelligence record or None
    """
    result = await db.execute(
        select(JobIntelligence)
        .where(JobIntelligence.job_id == job_id)
        .order_by(JobIntelligence.created_at.desc())
    )
    return result.scalar_one_or_none()


async def generate_candidate_intelligence(
    db: AsyncSession,
    candidate_id: UUID,
) -> CandidateIntelligence:
    """Generate candidate intelligence analytics.
    
    Deletes existing intelligence and creates new record.
    
    Args:
        db: Database session
        candidate_id: Candidate UUID
        
    Returns:
        CandidateIntelligence record
    """
    # Delete existing intelligence for this candidate
    await db.execute(
        delete(CandidateIntelligence).where(
            CandidateIntelligence.candidate_id == candidate_id
        )
    )

    # Calculate intelligence metrics
    metrics = await IntelligenceEngine.calculate_candidate_intelligence(db, candidate_id)

    # Create new intelligence record
    intelligence = CandidateIntelligence(
        candidate_id=candidate_id,
        market_competitiveness_score=metrics["market_competitiveness_score"],
        versatility_index=metrics["versatility_index"],
        skill_depth_score=metrics["skill_depth_score"],
        growth_potential_score=metrics["growth_potential_score"],
        breakdown=metrics["breakdown"],
    )

    db.add(intelligence)
    await db.commit()
    await db.refresh(intelligence)

    return intelligence


async def get_candidate_intelligence(
    db: AsyncSession,
    candidate_id: UUID,
) -> CandidateIntelligence | None:
    """Get candidate intelligence by candidate ID.
    
    Args:
        db: Database session
        candidate_id: Candidate UUID
        
    Returns:
        CandidateIntelligence record or None
    """
    result = await db.execute(
        select(CandidateIntelligence)
        .where(CandidateIntelligence.candidate_id == candidate_id)
        .order_by(CandidateIntelligence.created_at.desc())
    )
    return result.scalar_one_or_none()


async def generate_skill_intelligence(
    db: AsyncSession,
    skill_id: UUID,
) -> SkillIntelligence:
    """Generate skill intelligence analytics.
    
    Deletes existing intelligence and creates new record.
    
    Args:
        db: Database session
        skill_id: Skill UUID
        
    Returns:
        SkillIntelligence record
    """
    # Delete existing intelligence for this skill
    await db.execute(
        delete(SkillIntelligence).where(SkillIntelligence.skill_id == skill_id)
    )

    # Calculate intelligence metrics
    metrics = await IntelligenceEngine.calculate_skill_intelligence(db, skill_id)

    # Create new intelligence record
    intelligence = SkillIntelligence(
        skill_id=skill_id,
        demand_count=metrics["demand_count"],
        supply_count=metrics["supply_count"],
        scarcity_ratio=metrics["scarcity_ratio"],
        avg_required_level=metrics["avg_required_level"],
        breakdown=metrics["breakdown"],
    )

    db.add(intelligence)
    await db.commit()
    await db.refresh(intelligence)

    return intelligence


async def get_skill_intelligence(
    db: AsyncSession,
    skill_id: UUID,
) -> SkillIntelligence | None:
    """Get skill intelligence by skill ID.
    
    Args:
        db: Database session
        skill_id: Skill UUID
        
    Returns:
        SkillIntelligence record or None
    """
    result = await db.execute(
        select(SkillIntelligence)
        .where(SkillIntelligence.skill_id == skill_id)
        .order_by(SkillIntelligence.created_at.desc())
    )
    return result.scalar_one_or_none()


async def generate_match_intelligence(
    db: AsyncSession,
) -> MatchIntelligence:
    """Generate overall match intelligence analytics.
    
    Deletes existing intelligence and creates new record.
    
    Args:
        db: Database session
        
    Returns:
        MatchIntelligence record
    """
    # Delete all existing match intelligence (keep only latest)
    await db.execute(delete(MatchIntelligence))

    # Calculate intelligence metrics
    metrics = await IntelligenceEngine.calculate_match_intelligence(db)

    # Create new intelligence record
    intelligence = MatchIntelligence(
        score_distribution=metrics["score_distribution"],
        top_percentile_score=metrics["top_percentile_score"],
        low_match_ratio=metrics["low_match_ratio"],
        recommendation_quality_index=metrics["recommendation_quality_index"],
    )

    db.add(intelligence)
    await db.commit()
    await db.refresh(intelligence)

    return intelligence


async def get_match_intelligence(
    db: AsyncSession,
) -> MatchIntelligence | None:
    """Get latest match intelligence.
    
    Args:
        db: Database session
        
    Returns:
        MatchIntelligence record or None
    """
    result = await db.execute(
        select(MatchIntelligence)
        .order_by(MatchIntelligence.created_at.desc())
    )
    return result.scalar_one_or_none()


async def generate_recruiter_performance(
    db: AsyncSession,
    recruiter_id: UUID,
) -> RecruiterPerformance:
    """Generate recruiter performance analytics.
    
    Deletes existing performance data and creates new record.
    
    Args:
        db: Database session
        recruiter_id: Recruiter (user) UUID
        
    Returns:
        RecruiterPerformance record
    """
    # Delete existing performance for this recruiter
    await db.execute(
        delete(RecruiterPerformance).where(
            RecruiterPerformance.recruiter_id == recruiter_id
        )
    )

    # Calculate performance metrics
    metrics = await IntelligenceEngine.calculate_recruiter_performance(db, recruiter_id)

    # Create new performance record
    performance = RecruiterPerformance(
        recruiter_id=recruiter_id,
        recommendation_acceptance_rate=metrics["recommendation_acceptance_rate"],
        avg_time_to_hire=metrics["avg_time_to_hire"],
        hire_success_rate=metrics["hire_success_rate"],
        breakdown=metrics["breakdown"],
    )

    db.add(performance)
    await db.commit()
    await db.refresh(performance)

    return performance


async def get_recruiter_performance(
    db: AsyncSession,
    recruiter_id: UUID,
) -> RecruiterPerformance | None:
    """Get recruiter performance by recruiter ID.
    
    Args:
        db: Database session
        recruiter_id: Recruiter (user) UUID
        
    Returns:
        RecruiterPerformance record or None
    """
    result = await db.execute(
        select(RecruiterPerformance)
        .where(RecruiterPerformance.recruiter_id == recruiter_id)
        .order_by(RecruiterPerformance.created_at.desc())
    )
    return result.scalar_one_or_none()
