"""add processing blocked enum

Revision ID: 125fc5dd1b81
Revises: 331723522908
Create Date: 2026-07-13 18:19:41.928163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '125fc5dd1b81'
down_revision: Union[str, Sequence[str], None] = '331723522908'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE systemrecommendation ADD VALUE IF NOT EXISTS 'PROCESSING_BLOCKED'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
