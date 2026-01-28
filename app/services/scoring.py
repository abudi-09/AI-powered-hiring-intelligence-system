from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobSkillInput:
    skill_id: str
    skill_name: str
    weight: float


@dataclass(frozen=True)
class CandidateSkillInput:
    skill_id: str
    skill_name: str
    level: str | None
    years_experience: float | None


def normalize_weight(weight: float | None) -> float:
    if weight is None:
        return 1.0
    return max(weight, 0.0)


def calculate_weighted_match_score(
    job_skills: list[JobSkillInput],
    candidate_skills: list[CandidateSkillInput],
) -> tuple[float, dict]:
    """Compute weighted candidate-job compatibility from skill overlap."""
    if not job_skills:
        return 0.0, {
            "strategy": "skill_overlap_weighted_v1",
            "reason": "Job has no required skills",
            "matched_skills": [],
            "missing_skills": [],
            "weighted_contribution": 0.0,
            "experience_bonus": 0.0,
            "final_score": 0.0,
        }

    candidate_skill_map = {skill.skill_id: skill for skill in candidate_skills}
    matched_skills: list[dict] = []
    missing_skills: list[dict] = []
    total_weight = 0.0
    matched_weight = 0.0
    experience_bonus = 0.0

    for job_skill in job_skills:
        weight = normalize_weight(job_skill.weight)
        total_weight += weight

        candidate_skill = candidate_skill_map.get(job_skill.skill_id)
        if candidate_skill is None:
            missing_skills.append(
                {
                    "skill_id": job_skill.skill_id,
                    "skill_name": job_skill.skill_name,
                    "weight": weight,
                    "penalty": weight * 5.0,
                }
            )
            continue

        matched_weight += weight
        years_exp = candidate_skill.years_experience or 0.0
        exp_bonus = min(years_exp * 2.0, 10.0)
        experience_bonus += exp_bonus
        matched_skills.append(
            {
                "skill_id": job_skill.skill_id,
                "skill_name": job_skill.skill_name,
                "weight": weight,
                "level": candidate_skill.level,
                "years_experience": years_exp,
                "experience_bonus": exp_bonus,
            }
        )

    base_score = (matched_weight / total_weight * 100.0) if total_weight > 0 else 0.0
    missing_penalty = sum(skill["penalty"] for skill in missing_skills)
    final_score = max(0.0, min(100.0, base_score + experience_bonus - missing_penalty))

    explanation = {
        "strategy": "skill_overlap_weighted_v1",
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "weighted_contribution": round(base_score, 2),
        "experience_bonus": round(experience_bonus, 2),
        "missing_penalty": round(missing_penalty, 2),
        "final_score": round(final_score, 2),
        "total_job_skills": len(job_skills),
        "total_matched": len(matched_skills),
        "total_missing": len(missing_skills),
    }
    return final_score, explanation
