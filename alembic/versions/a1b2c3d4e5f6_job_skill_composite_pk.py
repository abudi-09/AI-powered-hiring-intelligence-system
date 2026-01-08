"""recreate job_skills as composite PK association

Revision ID: a1b2c3d4e5f6
Revises: c2b4e16e2f91
Create Date: 2026-01-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "5084e68c4dc2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing table if it used a surrogate PK
    op.drop_table("job_skills")

    # Create the new association table with composite primary key
    op.create_table(
        "job_skills",
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("job_id", "skill_id"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    # Recreate the old table with surrogate id column (simplified)
    op.drop_table("job_skills")
    op.create_table(
        "job_skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
    )
