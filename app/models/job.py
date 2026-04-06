from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.job_skill import JobSkill


if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.match import MatchScore
    from app.models.skill import Skill
    from app.models.user import User


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=JobStatus.OPEN.value,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped["User"] = relationship("User", back_populates="jobs")

    skills: Mapped[list["JobSkill"]] = relationship(
        "JobSkill",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    match_scores: Mapped[list["MatchScore"]] = relationship(
        "MatchScore",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    candidates: Mapped[list["Candidate"]] = relationship(
        "Candidate",
        secondary="match_scores",
        viewonly=True,
    )
