from __future__ import annotations

import uuid

from pydantic import BaseModel


class JobAnalyticsRead(BaseModel):
    job_id: uuid.UUID
    job_title: str
    average_match_score: float
    candidate_count: int
    hiring_difficulty_score: float
    top_candidate_score: float | None
    skill_count: int


class CandidateAnalyticsRead(BaseModel):
    candidate_id: uuid.UUID
    candidate_name: str
    best_job_score: float | None
    average_score: float
    versatility_score: int
    skill_gap_count: int
    matched_job_count: int


class SkillDemandRead(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    demand_count: int
    supply_count: int
    scarcity_ratio: float


class MatchDistributionBucket(BaseModel):
    range_start: int
    range_end: int
    count: int
    percentage: float


class MatchDistributionRead(BaseModel):
    total_matches: int
    buckets: list[MatchDistributionBucket]
    average_score: float
    median_bucket: str
