import pytest

from app.schemas.pagination import PaginatedResponse, PaginationParams


def test_pagination_params_defaults() -> None:
    params = PaginationParams()
    assert params.skip == 0
    assert params.limit == 50


def test_pagination_params_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError):
        PaginationParams(limit=0)


def test_paginated_response_wraps_items() -> None:
    page = PaginatedResponse[str](
        items=["a", "b"],
        total=10,
        skip=0,
        limit=2,
    )
    assert page.items == ["a", "b"]
    assert page.total == 10
