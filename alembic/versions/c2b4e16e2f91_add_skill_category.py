"""add skill category

Revision ID: c2b4e16e2f91
Revises: 5084e68c4dc2
Create Date: 2026-01-07

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2b4e16e2f91"
down_revision = "5084e68c4dc2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("skills", sa.Column("category", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("skills", "category")
