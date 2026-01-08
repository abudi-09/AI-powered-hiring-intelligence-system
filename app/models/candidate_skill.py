from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="skill_links")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="candidate_links")
