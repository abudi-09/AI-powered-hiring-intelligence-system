from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedSkill:
    skill_name: str
    years_experience: float | None = None
    level: str | None = None


class SkillExtractor:
    """Extract structured skills from plain-text resumes."""

    _EXPERIENCE_PATTERN = re.compile(
        r"(?P<skill>[A-Za-z][A-Za-z0-9+#/. -]{1,40}?)"
        r"(?:\s*[\(\-–—]\s*(?P<years>\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?\.?))?",
        re.IGNORECASE,
    )
    _LEVEL_PATTERN = re.compile(
        r"\b(junior|mid|intermediate|senior|expert|lead)\b",
        re.IGNORECASE,
    )

    def extract_from_text(
        self,
        text: str,
        known_skill_names: list[str],
    ) -> list[ExtractedSkill]:
        normalized_text = " ".join(text.split())
        if not normalized_text or not known_skill_names:
            return []

        known_by_lower = {name.lower(): name for name in known_skill_names}
        found: dict[str, ExtractedSkill] = {}

        for skill_name in sorted(known_skill_names, key=len, reverse=True):
            pattern = re.compile(rf"\b{re.escape(skill_name)}\b", re.IGNORECASE)
            if not pattern.search(normalized_text):
                continue

            years = self._years_near_match(normalized_text, skill_name)
            level = self._level_near_match(normalized_text, skill_name)
            canonical = known_by_lower[skill_name.lower()]
            found[canonical.lower()] = ExtractedSkill(
                skill_name=canonical,
                years_experience=years,
                level=level,
            )

        return list(found.values())

    def _years_near_match(self, text: str, skill_name: str) -> float | None:
        window_pattern = re.compile(
            rf"{re.escape(skill_name)}.{{0,40}}?(\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?\.?)",
            re.IGNORECASE,
        )
        match = window_pattern.search(text)
        if not match:
            reverse_pattern = re.compile(
                rf"(\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?\.?).{{0,20}}?{re.escape(skill_name)}",
                re.IGNORECASE,
            )
            match = reverse_pattern.search(text)
        if not match:
            return None
        return float(match.group(1))

    def _level_near_match(self, text: str, skill_name: str) -> str | None:
        window_pattern = re.compile(
            rf"{re.escape(skill_name)}.{{0,30}}?(junior|mid|intermediate|senior|expert|lead)",
            re.IGNORECASE,
        )
        match = window_pattern.search(text)
        if match:
            return match.group(1).lower()
        return None
