"""recreate candidate_skills as composite PK association

Revision ID: b7c8d9e0f123
Revises: a1b2c3d4e5f6
Create Date: 2026-01-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "b7c8d9e0f123"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing table if it used a surrogate PK
    op.drop_table("candidate_skills")

    # Create the new association table with composite primary key
    op.create_table(
        "candidate_skills",
        sa.Column("candidate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("candidate_id", "skill_id"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    # Recreate the old table with surrogate id column (simplified)
    op.drop_table("candidate_skills")
    op.create_table(
        "candidate_skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )
