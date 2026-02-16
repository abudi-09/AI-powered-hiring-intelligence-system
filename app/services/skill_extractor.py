from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "node": "Node.js",
    "node.js": "Node.js",
    "react.js": "React",
    "golang": "Go",
}


@dataclass(frozen=True)
class ExtractedSkill:
    skill_name: str
    years_experience: float | None = None
    level: str | None = None


class SkillExtractor:
    """Extract structured skills from plain-text resumes."""

    _LEVEL_WORDS = ("junior", "mid", "intermediate", "senior", "expert", "lead")
    _SECTION_HEADER = re.compile(
        r"(?:^|\n)\s*(?:technical\s+)?skills?\s*[:\-]\s*",
        re.IGNORECASE,
    )
    _SECTION_STOP = re.compile(
        r"\n\s*(?:experience|education|work history|employment|projects|certifications)\s*[:\-]",
        re.IGNORECASE,
    )

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self.aliases = {**DEFAULT_SKILL_ALIASES, **(aliases or {})}

    def extract_from_text(
        self,
        text: str,
        known_skill_names: list[str],
    ) -> list[ExtractedSkill]:
        if not text.strip() or not known_skill_names:
            return []

        normalized_text = self._normalize_text(text)
        skills_section = self._extract_skills_section(text)
        search_text = (
            self._normalize_text(skills_section)
            if skills_section
            else normalized_text
        )

        known_by_lower = {name.lower(): name for name in known_skill_names}
        search_terms = self._build_search_terms(known_skill_names, known_by_lower)

        found: dict[str, ExtractedSkill] = {}
        for term, canonical in search_terms:
            canonical_lower = canonical.lower()
            if canonical_lower in found:
                continue

            if not self._term_in_text(search_text, term):
                continue

            years = self._find_years([search_text], term)
            level = self._find_level([search_text], term)
            found[canonical_lower] = ExtractedSkill(
                skill_name=known_by_lower[canonical_lower],
                years_experience=years,
                level=level,
            )

        return sorted(found.values(), key=lambda item: item.skill_name.lower())

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.split())

    def _extract_skills_section(self, text: str) -> str | None:
        header_match = self._SECTION_HEADER.search(text)
        if not header_match:
            return None

        remainder = text[header_match.end() :]
        stop_match = self._SECTION_STOP.search(remainder)
        section = remainder[: stop_match.start()] if stop_match else remainder
        cleaned = section.strip()
        return cleaned or None

    def _build_search_terms(
        self,
        known_skill_names: list[str],
        known_by_lower: dict[str, str],
    ) -> list[tuple[str, str]]:
        terms: list[tuple[str, str]] = []
        seen: set[str] = set()

        for skill_name in sorted(known_skill_names, key=len, reverse=True):
            key = skill_name.lower()
            if key not in seen:
                terms.append((skill_name, skill_name))
                seen.add(key)

            for alias, canonical in self.aliases.items():
                if canonical.lower() != key:
                    continue
                alias_key = alias.lower()
                if alias_key not in seen:
                    terms.append((alias, skill_name))
                    seen.add(alias_key)

        return terms

    def _term_in_text(self, text: str, term: str) -> bool:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        return pattern.search(text) is not None

    def _find_years(self, contexts: list[str], term: str) -> float | None:
        for context in contexts:
            years = self._years_near_match(context, term)
            if years is not None:
                return years
        return None

    def _find_level(self, contexts: list[str], term: str) -> str | None:
        for context in contexts:
            level = self._level_before_match(context, term)
            if level:
                return level
            level = self._level_after_match(context, term)
            if level:
                return level
        return None

    def _years_near_match(self, text: str, term: str) -> float | None:
        patterns = [
            re.compile(
                rf"{re.escape(term)}.{{0,40}}?(\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?\.?)",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?\.?).{{0,20}}?{re.escape(term)}",
                re.IGNORECASE,
            ),
            re.compile(
                rf"{re.escape(term)}\s*[\(\-–—]\s*(\d+(?:\.\d+)?)\s*(?:\+?\s*years?|yrs?\.?)?\s*\)?",
                re.IGNORECASE,
            ),
        ]
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return float(match.group(1))
        return None

    def _level_before_match(self, text: str, term: str) -> str | None:
        level_group = "|".join(self._LEVEL_WORDS)
        pattern = re.compile(
            rf"\b({level_group})\s+{re.escape(term)}\b",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return match.group(1).lower()
        return None

    def _level_after_match(self, text: str, term: str) -> str | None:
        level_group = "|".join(self._LEVEL_WORDS)
        pattern = re.compile(
            rf"\b{re.escape(term)}.{{0,30}}?({level_group})\b",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            return match.group(1).lower()
        return None
