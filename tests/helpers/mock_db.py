from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


def scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    return result


def all_result(rows: list):
    result = MagicMock()
    result.all.return_value = rows
    return result


def one_result(row):
    result = MagicMock()
    result.one.return_value = row
    result.one_or_none.return_value = row
    return result


def mock_async_session(responses: list):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=responses)
    return session
