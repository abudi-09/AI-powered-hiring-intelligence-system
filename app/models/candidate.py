from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.candidate_skill import CandidateSkill


if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.match import MatchScore
    from app.models.skill import Skill


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    resume_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Direct association links for management
    skill_links: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Convenience relationship to load skills via secondary table
    skills: Mapped[list["Skill"]] = relationship(
        "Skill",
        secondary=CandidateSkill.__table__,
        back_populates="candidates",
        viewonly=True,
    )

    match_scores: Mapped[list["MatchScore"]] = relationship(
        "MatchScore",
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        secondary="match_scores",
        viewonly=True,
    )
