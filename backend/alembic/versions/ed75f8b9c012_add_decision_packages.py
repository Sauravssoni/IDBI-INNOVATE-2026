"""add decision packages

Revision ID: ed75f8b9c012
Revises: fc4c9edd7015
Create Date: 2026-07-11 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ed75f8b9c012"
down_revision: Union[str, Sequence[str], None] = "fc4c9edd7015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_packages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("package_id", sa.String(), nullable=False),
        sa.Column("assessment_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("case_version", sa.Integer(), nullable=False),
        sa.Column("canonical_json", sa.JSON(), nullable=False),
        sa.Column("package_hash", sa.String(), nullable=False),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("feature_snapshot", sa.JSON(), nullable=False),
        sa.Column("engine_versions", sa.JSON(), nullable=False),
        sa.Column("human_actions", sa.JSON(), nullable=False),
        sa.Column("audit_tip_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decision_packages_package_id"), "decision_packages", ["package_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_decision_packages_package_id"), table_name="decision_packages")
    op.drop_table("decision_packages")
