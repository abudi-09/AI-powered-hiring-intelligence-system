"""Add job status column

Revision ID: c4d5e6f7a8b9
Revises: 6d8a4f4f3e31
Create Date: 2026-06-11 10:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "6d8a4f4f3e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="open",
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "status")
