"""add missing analyst enum values

Revision ID: 8a45193de2c9
Revises: 7c35182cf1b8
Create Date: 2026-07-06 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8a45193de2c9'
down_revision: Union[str, Sequence[str], None] = '7c35182cf1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding missing PostgreSQL enum values."""
    # In PostgreSQL, adding values to an enum type is done via ALTER TYPE ADD VALUE.
    # We use IF NOT EXISTS for safety and idempotency.
    op.execute("ALTER TYPE analystrecommendationaction ADD VALUE IF NOT EXISTS 'RECOMMEND_AS_REQUESTED'")
    op.execute("ALTER TYPE analystrecommendationaction ADD VALUE IF NOT EXISTS 'RECOMMEND_DECLINE'")


def downgrade() -> None:
    """Downgrade schema.
    
    Note: PostgreSQL enum-value removal is intentionally irreversible without dropping
    and recreating the type and all dependent table columns. Therefore, this migration
    is intentionally irreversible on downgrade.
    """
    pass
