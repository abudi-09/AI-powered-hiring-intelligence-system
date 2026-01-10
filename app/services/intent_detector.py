from __future__ import annotations

import re
import uuid
from enum import Enum


class Intent(str, Enum):
    JOB_ANALYSIS = "job_analysis"
    CANDIDATE_ANALYSIS = "candidate_analysis"
    RECOMMENDATION_REQUEST = "recommendation_request"
    INSIGHT_EXPLANATION = "insight_explanation"
    SKILL_GAP_ANALYSIS = "skill_gap_analysis"
    MATCH_EXPLANATION = "match_explanation"
    GENERAL_HELP = "general_help"


class IntentDetector:
    """Rule-based intent detection for recruiter queries."""

    JOB_PATTERNS = [
        r"\b(job|position|role|opening)\b",
        r"\bhiring\s+difficulty\b",
        r"\bhard\s+to\s+(hire|fill)\b",
        r"\bcandidate\s+pool\b",
    ]

    CANDIDATE_PATTERNS = [
        r"\b(candidate|applicant|person)\b",
        r"\bwho\s+(is|are)\s+the\s+(best|top)\b",
        r"\bqualified\s+candidates\b",
        r"\bshortlist\b",
    ]

    RECOMMENDATION_PATTERNS = [
        r"\brecommend(ation)?\b",
        r"\bsuggest\b",
        r"\bwho\s+should\s+i\b",
        r"\btop\s+\d+\b",
        r"\bbest\s+(match|fit)\b",
    ]

    INSIGHT_PATTERNS = [
        r"\bwhy\b",
        r"\bexplain\b",
        r"\breason\b",
        r"\bhow\s+come\b",
    ]

    SKILL_GAP_PATTERNS = [
        r"\bskill\s+gap\b",
        r"\bmissing\s+skill\b",
        r"\blacking\b",
        r"\bwhat\s+(skills|are)\s+missing\b",
    ]

    MATCH_PATTERNS = [
        r"\bmatch\s+score\b",
        r"\b\d+%\b",
        r"\bscoring\b",
        r"\bhow\s+did\s+\w+\s+score\b",
    ]

    def detect(self, query: str, context: dict | None = None) -> dict:
        """Detect intent from user query."""
        query_lower = query.lower()

        intent_scores = {
            Intent.JOB_ANALYSIS: self._score_patterns(query_lower, self.JOB_PATTERNS),
            Intent.CANDIDATE_ANALYSIS: self._score_patterns(query_lower, self.CANDIDATE_PATTERNS),
            Intent.RECOMMENDATION_REQUEST: self._score_patterns(query_lower, self.RECOMMENDATION_PATTERNS),
            Intent.INSIGHT_EXPLANATION: self._score_patterns(query_lower, self.INSIGHT_PATTERNS),
            Intent.SKILL_GAP_ANALYSIS: self._score_patterns(query_lower, self.SKILL_GAP_PATTERNS),
            Intent.MATCH_EXPLANATION: self._score_patterns(query_lower, self.MATCH_PATTERNS),
        }

        max_intent = max(intent_scores.items(), key=lambda x: x[1])

        if max_intent[1] == 0:
            intent = Intent.GENERAL_HELP
            confidence = 0.5
        else:
            intent = max_intent[0]
            confidence = min(max_intent[1] / 3.0, 1.0)

        entities = self._extract_entities(query, context)

        return {
            "intent": intent.value,
            "confidence": confidence,
            "entities": entities,
        }

    def _score_patterns(self, query: str, patterns: list[str]) -> float:
        """Score query against pattern list."""
        score = 0.0
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 1.0
        return score

    def _extract_entities(self, query: str, context: dict | None) -> dict:
        """Extract entity references from query."""
        entities = {}

        uuid_pattern = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        uuid_matches = re.findall(uuid_pattern, query, re.IGNORECASE)
        if uuid_matches:
            entities["entity_id"] = uuid_matches[0]

        if context:
            if "last_entity_type" in context:
                entities["entity_type"] = context["last_entity_type"]
            if "last_entity_id" in context and "entity_id" not in entities:
                entities["entity_id"] = context["last_entity_id"]

        if "job" in query.lower():
            entities["entity_type"] = "job"
        elif "candidate" in query.lower():
            entities["entity_type"] = "candidate"

        return entities
