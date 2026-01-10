from __future__ import annotations

import uuid


class QueryPlanner:
    """Plans which engines to invoke based on detected intent."""

    INTENT_PLANS = {
        "job_analysis": [
            "fetch_job_analytics",
            "fetch_job_insights",
            "fetch_job_matches",
        ],
        "candidate_analysis": [
            "fetch_candidate_analytics",
            "fetch_candidate_insights",
            "fetch_candidate_matches",
        ],
        "recommendation_request": [
            "fetch_recommendations",
            "fetch_analytics",
            "fetch_insights",
            "generate_narrative",
        ],
        "insight_explanation": [
            "fetch_insights",
            "fetch_analytics",
            "generate_narrative",
        ],
        "skill_gap_analysis": [
            "fetch_analytics",
            "fetch_insights",
            "fetch_skill_demand",
        ],
        "match_explanation": [
            "fetch_match_score",
            "fetch_analytics",
            "generate_narrative",
        ],
        "general_help": [
            "generate_help_response",
        ],
    }

    def plan(self, intent: str, entities: dict) -> dict:
        """Create execution plan based on intent and entities."""
        steps = self.INTENT_PLANS.get(intent, ["generate_help_response"])

        needs_entity = intent not in ["general_help"]
        has_entity = "entity_id" in entities and "entity_type" in entities

        if needs_entity and not has_entity:
            return {
                "intent": intent,
                "steps": ["request_clarification"],
                "requires_entity": True,
                "entities": entities,
            }

        return {
            "intent": intent,
            "steps": steps,
            "requires_entity": needs_entity,
            "entities": entities,
        }
