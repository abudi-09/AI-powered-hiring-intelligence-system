"""Intelligence API routes for dashboard analytics."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, role_required
from app.crud import intelligence as intelligence_crud
from app.models.user import User, UserRole
from app.schemas.intelligence import (
    CandidateIntelligenceRead,
    JobIntelligenceRead,
    MatchIntelligenceRead,
    RecruiterPerformanceRead,
    SkillIntelligenceRead,
)


router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

AllowedRoleDep = role_required(UserRole.Admin, UserRole.Recruiter, UserRole.HiringManager)


# Job Intelligence Routes
@router.get(
    "/job/{job_id}",
    response_model=JobIntelligenceRead,
    status_code=status.HTTP_200_OK,
)
async def get_job_intelligence(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> JobIntelligenceRead:
    """Get job intelligence analytics.
    
    Returns the latest intelligence metrics for a job.
    """
    intelligence = await intelligence_crud.get_job_intelligence(db, job_id)
    if not intelligence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job intelligence not found for job {job_id}",
        )
    return intelligence


@router.post(
    "/generate/job/{job_id}",
    response_model=JobIntelligenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_job_intelligence(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> JobIntelligenceRead:
    """Generate job intelligence analytics.
    
    Calculates and stores intelligence metrics for a job.
    Replaces any existing intelligence data.
    """
    try:
        intelligence = await intelligence_crud.generate_job_intelligence(db, job_id)
        return intelligence
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# Candidate Intelligence Routes
@router.get(
    "/candidate/{candidate_id}",
    response_model=CandidateIntelligenceRead,
    status_code=status.HTTP_200_OK,
)
async def get_candidate_intelligence(
    candidate_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> CandidateIntelligenceRead:
    """Get candidate intelligence analytics.
    
    Returns the latest intelligence metrics for a candidate.
    """
    intelligence = await intelligence_crud.get_candidate_intelligence(db, candidate_id)
    if not intelligence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate intelligence not found for candidate {candidate_id}",
        )
    return intelligence


@router.post(
    "/generate/candidate/{candidate_id}",
    response_model=CandidateIntelligenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_candidate_intelligence(
    candidate_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> CandidateIntelligenceRead:
    """Generate candidate intelligence analytics.
    
    Calculates and stores intelligence metrics for a candidate.
    Replaces any existing intelligence data.
    """
    try:
        intelligence = await intelligence_crud.generate_candidate_intelligence(db, candidate_id)
        return intelligence
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

# Skill Intelligence Routes
@router.get(
    "/skill/{skill_id}",
    response_model=SkillIntelligenceRead,
    status_code=status.HTTP_200_OK,
)
async def get_skill_intelligence(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> SkillIntelligenceRead:
    """Get skill intelligence analytics.
    
    Returns the latest intelligence metrics for a skill.
    """
    intelligence = await intelligence_crud.get_skill_intelligence(db, skill_id)
    if not intelligence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill intelligence not found for skill {skill_id}",
        )
    return intelligence


@router.post(
    "/generate/skill/{skill_id}",
    response_model=SkillIntelligenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_skill_intelligence(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> SkillIntelligenceRead:
    """Generate skill intelligence analytics.
    
    Calculates and stores intelligence metrics for a skill.
    Replaces any existing intelligence data.
    """
    try:
        intelligence = await intelligence_crud.generate_skill_intelligence(db, skill_id)
        return intelligence
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# Match Intelligence Routes
@router.get(
    "/match/summary",
    response_model=MatchIntelligenceRead,
    status_code=status.HTTP_200_OK,
)
async def get_match_intelligence(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> MatchIntelligenceRead:
    """Get overall match intelligence analytics.
    
    Returns the latest match quality and recommendation metrics.
    """
    intelligence = await intelligence_crud.get_match_intelligence(db)
    if not intelligence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match intelligence not found. Generate it first.",
        )
    return intelligence


@router.post(
    "/generate/match",
    response_model=MatchIntelligenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_match_intelligence(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> MatchIntelligenceRead:
    """Generate overall match intelligence analytics.
    
    Calculates and stores match quality metrics across all matches.
    Replaces any existing intelligence data.
    """
    intelligence = await intelligence_crud.generate_match_intelligence(db)
    return intelligence

# Recruiter Performance Routes
@router.get(
    "/recruiter/{recruiter_id}",
    response_model=RecruiterPerformanceRead,
    status_code=status.HTTP_200_OK,
)
async def get_recruiter_performance(
    recruiter_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> RecruiterPerformanceRead:
    """Get recruiter performance analytics.  
    Returns the latest performance metrics for a recruiter.
    """
    performance = await intelligence_crud.get_recruiter_performance(db, recruiter_id)
    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recruiter performance not found for recruiter {recruiter_id}",
        )
    return performance
@router.post(
    "/generate/recruiter/{recruiter_id}",
    response_model=RecruiterPerformanceRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_recruiter_performance(
    recruiter_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: User = Depends(AllowedRoleDep),
) -> RecruiterPerformanceRead:
    """Generate recruiter performance analytics.
    
    Calculates and stores performance metrics for a recruiter.
    Replaces any existing performance data.
    """
    try:
        performance = await intelligence_crud.generate_recruiter_performance(db, recruiter_id)
        return performance
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
