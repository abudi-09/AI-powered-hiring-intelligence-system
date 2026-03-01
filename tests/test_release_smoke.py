from app.main import create_app


def test_create_app_registers_health_and_chat_routes() -> None:
    app = create_app()
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/health" in paths
    assert "/ready" in paths
    assert "/chat/query" in paths
    assert "/jobs/{job_id}/matches/auto-score" in paths


def test_openapi_documents_core_hiring_surface() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]

    assert "/auth/login" in paths
    assert "/candidates/{candidate_id}/skills/extract-from-resume" in paths
    assert "/jobs/{job_id}/matches/auto-score" in paths
    assert "/intelligence/recruiter/{recruiter_id}" in paths
    assert "/matches/auto-score" in paths


def test_openapi_title_matches_product_name() -> None:
    schema = create_app().openapi()
    assert schema["info"]["title"] == "AI Powered Hiring System"
