from app.services.intent_detector import Intent, IntentDetector


def test_detects_recommendation_intent() -> None:
    detector = IntentDetector()
    result = detector.detect("Who should I recommend for this backend role?")
    assert result["intent"] == Intent.RECOMMENDATION_REQUEST.value
    assert result["confidence"] > 0.0


def test_detects_skill_gap_intent() -> None:
    detector = IntentDetector()
    result = detector.detect("What is the skill gap on this requisition?")
    assert result["intent"] == Intent.SKILL_GAP_ANALYSIS.value


def test_falls_back_to_general_help() -> None:
    detector = IntentDetector()
    result = detector.detect("hello there")
    assert result["intent"] == Intent.GENERAL_HELP.value
