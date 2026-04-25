import uuid
from datetime import datetime, timezone

import pytest

from app.services.skill_extractor import SkillExtractor


@pytest.fixture
def extractor() -> SkillExtractor:
    return SkillExtractor()


def test_extracts_known_skills_with_experience(extractor: SkillExtractor) -> None:
    text = """
    Jane Doe
    Senior Python developer with 6 years of experience.
    Also worked with React (2 years) and SQL.
    """
    extracted = extractor.extract_from_text(text, ["Python", "React", "SQL", "Go"])
    by_name = {item.skill_name: item for item in extracted}

    assert by_name["Python"].years_experience == pytest.approx(6.0)
    assert by_name["Python"].level == "senior"
    assert by_name["React"].years_experience == pytest.approx(2.0)
    assert "SQL" in by_name
    assert "Go" not in by_name


def test_returns_empty_for_blank_resume(extractor: SkillExtractor) -> None:
    assert extractor.extract_from_text("   ", ["Python"]) == []


def test_maps_js_alias_to_javascript(extractor: SkillExtractor) -> None:
    text = "Primary stack: JS (5 yrs) for frontend work."
    extracted = extractor.extract_from_text(text, ["JavaScript", "React"])
    by_name = {item.skill_name: item for item in extracted}

    assert "JavaScript" in by_name
    assert by_name["JavaScript"].years_experience == pytest.approx(5.0)


def test_maps_postgres_alias_to_postgresql(extractor: SkillExtractor) -> None:
    text = "Database experience with Postgres over 4 years."
    extracted = extractor.extract_from_text(text, ["PostgreSQL", "SQL"])

    assert len(extracted) == 1
    assert extracted[0].skill_name == "PostgreSQL"
    assert extracted[0].years_experience == pytest.approx(4.0)


def test_parses_dedicated_skills_section(extractor: SkillExtractor) -> None:
    text = """
    Profile summary with unrelated keywords like Go and Rust.

    Skills:
    Python, React, SQL

    Experience:
    Built hiring dashboards.
    """
    extracted = extractor.extract_from_text(text, ["Python", "React", "SQL", "Go", "Rust"])
    names = {item.skill_name for item in extracted}

    assert names == {"Python", "React", "SQL"}


def test_technical_skills_header_is_supported(extractor: SkillExtractor) -> None:
    text = """
    Technical Skills - JavaScript, TypeScript, Node.js
    Experience:
    Platform engineer.
    """
    catalog = ["JavaScript", "TypeScript", "Node.js"]
    extracted = extractor.extract_from_text(text, catalog)
    names = {item.skill_name for item in extracted}

    assert names == {"JavaScript", "TypeScript", "Node.js"}


def test_detects_level_before_skill_name(extractor: SkillExtractor) -> None:
    text = "Expert Go developer with 3 years backend experience."
    extracted = extractor.extract_from_text(text, ["Go"])

    assert extracted[0].level == "expert"
    assert extracted[0].years_experience == pytest.approx(3.0)


def test_parenthetical_years_format(extractor: SkillExtractor) -> None:
    text = "Worked extensively with React (3.5 years)."
    extracted = extractor.extract_from_text(text, ["React"])

    assert extracted[0].years_experience == pytest.approx(3.5)


def test_deduplicates_canonical_and_alias_matches(extractor: SkillExtractor) -> None:
    text = "JavaScript and JS used daily for 7 years."
    extracted = extractor.extract_from_text(text, ["JavaScript"])

    assert len(extracted) == 1
    assert extracted[0].skill_name == "JavaScript"


def test_custom_aliases_can_extend_defaults(extractor: SkillExtractor) -> None:
    custom = SkillExtractor(aliases={"k8s": "Kubernetes"})
    text = "Infrastructure: k8s (2 yrs)."
    extracted = custom.extract_from_text(text, ["Kubernetes"])

    assert extracted[0].skill_name == "Kubernetes"
    assert extracted[0].years_experience == pytest.approx(2.0)


def test_returns_sorted_skill_names(extractor: SkillExtractor) -> None:
    text = "Skills: SQL, Python, React"
    extracted = extractor.extract_from_text(text, ["Python", "React", "SQL"])

    assert [item.skill_name for item in extracted] == ["Python", "React", "SQL"]


def test_extracts_c_plus_plus_without_word_boundaries(extractor: SkillExtractor) -> None:
    text = "Systems programming in C++ for 5 years."
    extracted = extractor.extract_from_text(text, ["C++", "Python"])

    assert len(extracted) == 1
    assert extracted[0].skill_name == "C++"
    assert extracted[0].years_experience == pytest.approx(5.0)


def test_extracts_dotnet_skill_name(extractor: SkillExtractor) -> None:
    text = "Backend built with .NET and SQL."
    extracted = extractor.extract_from_text(text, [".NET", "SQL"])
    names = {item.skill_name for item in extracted}

    assert names == {".NET", "SQL"}


def test_extract_skills_section_returns_none_without_header(extractor: SkillExtractor) -> None:
    assert extractor._extract_skills_section("General developer profile.") is None
