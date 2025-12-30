from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Ensure model modules are imported so Base.metadata is fully populated
# when migration tooling scans the project.
from app import models as _models  # noqa: E402,F401
