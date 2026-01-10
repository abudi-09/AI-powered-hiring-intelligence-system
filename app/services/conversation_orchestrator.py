from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.match import get_matches_by_job, get_matches_by_candidate
from app.crud.recommendation import list_recommendations
from app.services.analytics_engine import AnalyticsEngine
from app.services.insight_engine import InsightEngine
from app.services.narrative_engine import NarrativeEngine, MockLLMProvider


class ConversationOrchestrator:
    """Orchestrates engine calls based on query plan."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics = AnalyticsEngine(db)
        self.insight_engine = InsightEngine(db)
        self.narrative_engine = NarrativeEngine(MockLLMProvider())

    async def execute_plan(self, plan: dict) -> dict:
        """Execute query plan and gather structured data."""
        intent = plan["intent"]
        steps = plan["steps"]
        entities = plan["entities"]

        if "request_clarification" in steps:
            return await self._handle_clarification(intent, entities)

        if "generate_help_response" in steps:
            return await self._handle_help_request()

        collected_data = {
            "intent": intent,
            "entities": entities,
            "analytics": None,
            "insights": None,
            "recommendations": None,
            "matches": None,
            "narratives": [],
        }

        entity_id = entities.get("entity_id")
        entity_type = entities.get("entity_type")

        if entity_id:
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                return await self._handle_invalid_entity()

        for step in steps:
            if step == "fetch_job_analytics" and entity_type == "job":
                collected_data["analytics"] = await self.analytics.compute_job_analytics(entity_id)

            elif step == "fetch_candidate_analytics" and entity_type == "candidate":
                collected_data["analytics"] = await self.analytics.compute_candidate_analytics(entity_id)

            elif step == "fetch_analytics":
                if entity_type == "job":
                    collected_data["analytics"] = await self.analytics.compute_job_analytics(entity_id)
                elif entity_type == "candidate":
                    collected_data["analytics"] = await self.analytics.compute_candidate_analytics(entity_id)

            elif step == "fetch_job_insights" and entity_type == "job":
                collected_data["insights"] = await self.insight_engine.generate_job_insights(entity_id)

            elif step == "fetch_candidate_insights" and entity_type == "candidate":
                collected_data["insights"] = await self.insight_engine.generate_candidate_insights(entity_id)

            elif step == "fetch_insights":
                if entity_type == "job":
                    collected_data["insights"] = await self.insight_engine.generate_job_insights(entity_id)
                elif entity_type == "candidate":
                    collected_data["insights"] = await self.insight_engine.generate_candidate_insights(entity_id)

            elif step == "fetch_job_matches" and entity_type == "job":
                collected_data["matches"] = await get_matches_by_job(self.db, entity_id)

            elif step == "fetch_candidate_matches" and entity_type == "candidate":
                collected_data["matches"] = await get_matches_by_candidate(self.db, entity_id)

            elif step == "fetch_recommendations":
                recommendations = await list_recommendations(self.db, entity_type, entity_id)
                collected_data["recommendations"] = recommendations

            elif step == "fetch_skill_demand":
                collected_data["skill_demand"] = await self.analytics.compute_skill_demand()

        return collected_data

    async def compose_response(self, collected_data: dict, query: str) -> dict:
        """Compose final chat response from collected data."""
        intent = collected_data["intent"]
        analytics = collected_data.get("analytics")
        insights = collected_data.get("insights", [])
        recommendations = collected_data.get("recommendations", [])

        message_parts = []
        bullets = []
        sources = []
        confidence = 0.0

        if intent == "job_analysis":
            if analytics:
                message_parts.append(
                    f"Job analysis shows an average match score of {analytics.get('average_match_score', 0):.1f}% "
                    f"across {analytics.get('candidate_count', 0)} candidates. "
                    f"Hiring difficulty is rated {analytics.get('hiring_difficulty_score', 0):.0f}/100."
                )
                bullets.append(f"Average Match: {analytics.get('average_match_score', 0):.1f}%")
                bullets.append(f"Candidate Pool: {analytics.get('candidate_count', 0)}")
                bullets.append(f"Hiring Difficulty: {analytics.get('hiring_difficulty_score', 0):.0f}/100")
                sources.append("analytics")
                confidence = 90.0

            if insights:
                high_severity = [i for i in insights if i.get("severity") == "high"]
                if high_severity:
                    message_parts.append(
                        f"{len(high_severity)} high-priority insight(s) detected requiring attention."
                    )
                    bullets.append(f"High Priority Insights: {len(high_severity)}")
                sources.append("insights")
                confidence = max(confidence, 85.0)

        elif intent == "candidate_analysis":
            if analytics:
                message_parts.append(
                    f"Candidate shows {analytics.get('average_score', 0):.1f}% average match score "
                    f"across {analytics.get('matched_job_count', 0)} jobs. "
                    f"Versatility score: {analytics.get('versatility_score', 0)} (jobs scoring 60%+)."
                )
                bullets.append(f"Average Score: {analytics.get('average_score', 0):.1f}%")
                bullets.append(f"Matched Jobs: {analytics.get('matched_job_count', 0)}")
                bullets.append(f"Versatility: {analytics.get('versatility_score', 0)} jobs")
                sources.append("analytics")
                confidence = 90.0

            if insights:
                strengths = [i for i in insights if i.get("insight_type") == "candidate_strength"]
                if strengths:
                    message_parts.append(f"{len(strengths)} strength indicator(s) identified.")
                    bullets.append(f"Strengths: {len(strengths)}")
                sources.append("insights")
                confidence = max(confidence, 85.0)

        elif intent == "recommendation_request":
            if recommendations:
                top_rec = recommendations[0]
                message_parts.append(
                    f"Top recommendation: Rank #{top_rec.rank} with {top_rec.score:.1f}% score "
                    f"and {top_rec.confidence:.0f}% confidence. "
                )
                bullets.append(f"Top Score: {top_rec.score:.1f}%")
                bullets.append(f"Confidence: {top_rec.confidence:.0f}%")
                bullets.append(f"Total Recommendations: {len(recommendations)}")
                sources.append("recommendations")
                confidence = top_rec.confidence
            else:
                message_parts.append("No recommendations available for this entity yet.")
                confidence = 50.0

        elif intent == "insight_explanation":
            if insights:
                message_parts.append(f"Found {len(insights)} insight(s) for this entity.")
                for insight in insights[:3]:
                    bullets.append(f"{insight.get('title')} ({insight.get('severity')})")
                sources.append("insights")
                confidence = 85.0
            else:
                message_parts.append("No insights generated for this entity yet.")
                confidence = 60.0

        elif intent == "skill_gap_analysis":
            if analytics and "skill_gap_count" in analytics:
                gap_count = analytics.get("skill_gap_count", 0)
                message_parts.append(f"Analysis shows {gap_count} skill gap(s) identified.")
                bullets.append(f"Skill Gaps: {gap_count}")
                sources.append("analytics")
                confidence = 88.0
            else:
                message_parts.append("Skill gap analysis requires candidate context.")
                confidence = 60.0

        elif intent == "match_explanation":
            if collected_data.get("matches"):
                matches = collected_data["matches"]
                if matches:
                    top_match = matches[0]
                    message_parts.append(f"Top match scored {top_match.score:.1f}%.")
                    bullets.append(f"Match Score: {top_match.score:.1f}%")
                    sources.append("matches")
                    confidence = 85.0

        if not message_parts:
            message_parts.append("I need more context to answer this question. Please specify a job or candidate ID.")
            confidence = 50.0

        message = " ".join(message_parts)

        return {
            "message": message,
            "bullets": bullets,
            "confidence": confidence,
            "sources": sources,
        }

    async def _handle_clarification(self, intent: str, entities: dict) -> dict:
        """Handle requests requiring clarification."""
        return {
            "intent": intent,
            "entities": entities,
            "message": "I need more information. Please provide a job ID or candidate ID to continue.",
            "bullets": ["Missing: Entity ID", "Suggested: Include UUID in your query"],
            "confidence": 100.0,
            "sources": ["system"],
        }

    async def _handle_help_request(self) -> dict:
        """Handle general help requests."""
        return {
            "intent": "general_help",
            "entities": {},
            "message": (
                "I'm your AI recruiter assistant. I can help you with: job analysis, candidate analysis, "
                "recommendations, insights, skill gaps, and match explanations. "
                "Try asking 'Why is this job hard to hire for?' or 'Who are the top candidates?'"
            ),
            "bullets": [
                "Job Analysis",
                "Candidate Analysis",
                "Recommendations",
                "Insights & Skill Gaps",
                "Match Explanations",
            ],
            "confidence": 100.0,
            "sources": ["system"],
        }

    async def _handle_invalid_entity(self) -> dict:
        """Handle invalid entity ID format."""
        return {
            "intent": "error",
            "entities": {},
            "message": "The entity ID provided is not a valid UUID format. Please check and try again.",
            "bullets": ["Error: Invalid UUID format"],
            "confidence": 100.0,
            "sources": ["system"],
        }
