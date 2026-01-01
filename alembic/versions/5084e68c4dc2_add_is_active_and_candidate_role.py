"""Add is_active and candidate role

Revision ID: 5084e68c4dc2
Revises: 99ce610a8906
Create Date: 2026-01-01 13:27:25.787659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5084e68c4dc2'
down_revision: Union[str, Sequence[str], None] = '99ce610a8906'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add enum value (safe / idempotent).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'user_role' AND e.enumlabel = 'Candidate'
            ) THEN
                ALTER TYPE user_role ADD VALUE 'Candidate';
            END IF;
        END $$;
        """
    )

    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_active")

    # Downgrading enum values in PostgreSQL is non-trivial (requires type recreation);
    # we intentionally leave the 'Candidate' label in place.
