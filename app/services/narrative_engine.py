from __future__ import annotations

import uuid
from typing import Protocol

from app.models.recommendation import Recommendation


class LLMProvider(Protocol):
    """Protocol for LLM provider abstraction."""

    async def generate(self, prompt: str) -> str:
        """Generate text from prompt."""
        ...


class MockLLMProvider:
    """Mock LLM provider for deterministic testing and fallback."""

    async def generate(self, prompt: str) -> str:
        """Generate mock narrative using template-based logic."""
        return "Mock narrative generation. Replace with actual LLM provider."


class NarrativeEngine:
    """LLM-powered narrative generation engine for recommendations."""

    VERSION = "1.0.0"

    SYSTEM_PROMPTS = {
        "professional": (
            "You are a professional recruitment analyst. Generate clear, actionable "
            "narratives for hiring managers. Use precise language and focus on business value."
        ),
        "executive": (
            "You are an executive briefing assistant. Generate concise, high-level "
            "summaries focused on strategic hiring decisions and key risks."
        ),
        "neutral": (
            "You are a factual AI assistant. Generate objective, data-driven narratives "
            "without opinion or bias. State facts from the data provided."
        ),
        "technical": (
            "You are a technical hiring expert. Generate detailed, skill-focused "
            "narratives with emphasis on technical qualifications and competency gaps."
        ),
    }

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider or MockLLMProvider()

    async def generate_narrative(
        self,
        recommendation: Recommendation,
        tone: str = "professional",
        include_bullets: bool = True,
    ) -> dict:
        """Generate human-readable narrative from recommendation data."""
        prompt = self._build_prompt(recommendation, tone, include_bullets)

        narrative_text = await self.llm_provider.generate(prompt)

        if not narrative_text or narrative_text.startswith("Mock narrative"):
            narrative_text = self._generate_fallback_narrative(recommendation)

        summary_bullets = self._extract_bullets(recommendation) if include_bullets else []

        return {
            "recommendation_id": recommendation.id,
            "narrative_text": narrative_text,
            "summary_bullets": summary_bullets,
            "tone_used": tone,
            "confidence": recommendation.confidence,
            "version": self.VERSION,
        }

    def _build_prompt(
        self, recommendation: Recommendation, tone: str, include_bullets: bool
    ) -> str:
        """Build LLM prompt from recommendation data."""
        system_prompt = self.SYSTEM_PROMPTS.get(tone, self.SYSTEM_PROMPTS["professional"])

        explanation = recommendation.explanation
        rec_type = recommendation.recommendation_type

        if rec_type == "candidate_for_job":
            context = self._format_job_context(recommendation, explanation)
        else:
            context = self._format_candidate_context(recommendation, explanation)

        instruction = (
            f"Generate a {tone} narrative for this recommendation.\n\n"
            f"Rules:\n"
            f"- Only reference metrics present in the data\n"
            f"- Do not invent skills, scores, or details\n"
            f"- Use specific numbers from the explanation\n"
            f"- Keep narrative to 3-5 sentences\n"
            f"- Focus on actionable insights\n"
        )

        if include_bullets:
            instruction += "- End with 2-3 bullet point highlights\n"

        prompt = f"""{system_prompt}

{instruction}

Data:
{context}

Generate narrative:"""

        return prompt

    def _format_job_context(self, recommendation: Recommendation, explanation: dict) -> str:
        """Format job recommendation context for LLM."""
        base_score = explanation.get("base_match_score", 0)
        skill_gap_count = explanation.get("skill_gap_count", 0)
        skill_gap_penalty = explanation.get("skill_gap_penalty", 0)
        difficulty_penalty = explanation.get("difficulty_penalty", 0)
        hiring_difficulty = explanation.get("hiring_difficulty", 0)
        final_score = explanation.get("final_score", recommendation.score)

        return f"""Recommendation Type: Candidate for Job
Rank: {recommendation.rank}
Match Score: {base_score:.1f}%
Skill Gaps: {skill_gap_count}
Skill Gap Penalty: -{skill_gap_penalty:.1f}
Hiring Difficulty: {hiring_difficulty:.1f}/100
Difficulty Penalty: -{difficulty_penalty:.1f}
Final Score: {final_score:.1f}%
Confidence: {recommendation.confidence:.1f}%"""

    def _format_candidate_context(self, recommendation: Recommendation, explanation: dict) -> str:
        """Format candidate recommendation context for LLM."""
        base_score = explanation.get("base_match_score", 0)
        versatility_score = explanation.get("versatility_score", 0)
        versatility_bonus = explanation.get("versatility_bonus", 0)
        strength_bonus = explanation.get("strength_bonus", 0)
        has_strength = explanation.get("has_strength_insight", False)
        final_score = explanation.get("final_score", recommendation.score)

        return f"""Recommendation Type: Job for Candidate
Rank: {recommendation.rank}
Match Score: {base_score:.1f}%
Versatility Score: {versatility_score} jobs
Versatility Bonus: +{versatility_bonus:.1f}
Strength Insight: {"Yes" if has_strength else "No"}
Strength Bonus: +{strength_bonus:.1f}
Final Score: {final_score:.1f}%
Confidence: {recommendation.confidence:.1f}%"""

    def _generate_fallback_narrative(self, recommendation: Recommendation) -> str:
        """Generate deterministic fallback narrative when LLM unavailable."""
        explanation = recommendation.explanation
        rec_type = recommendation.recommendation_type

        if rec_type == "candidate_for_job":
            base_score = explanation.get("base_match_score", 0)
            skill_gap_count = explanation.get("skill_gap_count", 0)
            final_score = explanation.get("final_score", recommendation.score)

            narrative = (
                f"This candidate ranks #{recommendation.rank} with a {final_score:.1f}% match score "
                f"(base: {base_score:.1f}%). "
            )

            if skill_gap_count > 0:
                narrative += f"Analysis shows {skill_gap_count} skill gap(s) requiring attention. "
            else:
                narrative += "Skills align well with job requirements. "

            narrative += f"Recommendation confidence: {recommendation.confidence:.0f}%."

        else:
            base_score = explanation.get("base_match_score", 0)
            versatility_score = explanation.get("versatility_score", 0)
            final_score = explanation.get("final_score", recommendation.score)

            narrative = (
                f"This job ranks #{recommendation.rank} with a {final_score:.1f}% match score "
                f"(base: {base_score:.1f}%). "
            )

            if versatility_score > 0:
                narrative += f"Candidate shows versatility across {versatility_score} similar roles. "
            else:
                narrative += "Candidate profile shows specialized focus. "

            narrative += f"Recommendation confidence: {recommendation.confidence:.0f}%."

        return narrative

    def _extract_bullets(self, recommendation: Recommendation) -> list[str]:
        """Extract key bullet points from recommendation data."""
        explanation = recommendation.explanation
        bullets = []

        if recommendation.recommendation_type == "candidate_for_job":
            base_score = explanation.get("base_match_score", 0)
            skill_gap_count = explanation.get("skill_gap_count", 0)
            hiring_difficulty = explanation.get("hiring_difficulty", 0)

            bullets.append(f"Match Score: {base_score:.1f}% (Rank #{recommendation.rank})")

            if skill_gap_count > 0:
                bullets.append(f"Skill Gaps: {skill_gap_count} identified")
            else:
                bullets.append("Skills: Strong alignment")

            if hiring_difficulty > 70:
                bullets.append(f"Hiring Difficulty: High ({hiring_difficulty:.0f}/100)")
            elif hiring_difficulty > 50:
                bullets.append(f"Hiring Difficulty: Moderate ({hiring_difficulty:.0f}/100)")
            else:
                bullets.append(f"Hiring Difficulty: Low ({hiring_difficulty:.0f}/100)")

        else:
            base_score = explanation.get("base_match_score", 0)
            versatility_score = explanation.get("versatility_score", 0)
            has_strength = explanation.get("has_strength_insight", False)

            bullets.append(f"Match Score: {base_score:.1f}% (Rank #{recommendation.rank})")

            if versatility_score > 0:
                bullets.append(f"Versatility: {versatility_score} similar roles")
            else:
                bullets.append("Versatility: Specialized profile")

            if has_strength:
                bullets.append("Profile: Strength insights detected")

        bullets.append(f"Confidence: {recommendation.confidence:.0f}%")

        return bullets
