"""unique decision package seal boundary

Revision ID: 3f9b4d2a8c77
Revises: ed75f8b9c012
Create Date: 2026-07-11 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "3f9b4d2a8c77"
down_revision: Union[str, Sequence[str], None] = "ed75f8b9c012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_decision_package_case_version_assessment",
        "decision_packages",
        ["case_id", "case_version", "assessment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_decision_package_case_version_assessment",
        "decision_packages",
        type_="unique",
    )
