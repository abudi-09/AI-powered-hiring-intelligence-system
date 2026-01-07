from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.job_skill import JobSkill


if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job import Job


## JobSkill association now mapped as a model in app.models.job_skill


candidate_skills = Table(
    "candidate_skills",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "candidate_id",
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "skill_id",
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    jobs: Mapped[list["JobSkill"]] = relationship(
        "JobSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    candidates: Mapped[list["Candidate"]] = relationship(
        "Candidate",
        secondary=candidate_skills,
        back_populates="skills",
    )
