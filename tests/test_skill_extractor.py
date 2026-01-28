import pytest

from app.services.skill_extractor import SkillExtractor


def test_extracts_known_skills_with_experience() -> None:
    extractor = SkillExtractor()
    text = """
    Jane Doe
    Senior Python developer with 6 years of experience.
    Also worked with React (2 years) and SQL.
    """
    extracted = extractor.extract_from_text(text, ["Python", "React", "SQL", "Go"])
    by_name = {item.skill_name: item for item in extracted}

    assert "Python" in by_name
    assert by_name["Python"].years_experience == pytest.approx(6.0)
    assert "React" in by_name
    assert by_name["React"].years_experience == pytest.approx(2.0)
    assert "SQL" in by_name
    assert "Go" not in by_name


def test_returns_empty_for_blank_resume() -> None:
    extractor = SkillExtractor()
    assert extractor.extract_from_text("   ", ["Python"]) == []
