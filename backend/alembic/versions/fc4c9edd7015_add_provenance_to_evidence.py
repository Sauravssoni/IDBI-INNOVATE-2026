"""add provenance to evidence

Revision ID: fc4c9edd7015
Revises: 8a45193de2c9
Create Date: 2026-07-06 19:39:36.956756

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "fc4c9edd7015"
down_revision: Union[str, Sequence[str], None] = "8a45193de2c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EVIDENCE_TABLES = [
    "bank_transactions",
    "employment_periods",
    "gst_periods",
    "invoice_payments",
    "invoices",
    "obligations",
]


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in EVIDENCE_TABLES:
        op.add_column(table_name, sa.Column("consent_id_fk", sa.UUID(), nullable=True))
        op.add_column(
            table_name, sa.Column("data_connection_id_fk", sa.UUID(), nullable=True)
        )

        # Add nullable first
        op.add_column(
            table_name, sa.Column("ingestion_mode", sa.String(), nullable=True)
        )

        # Create indexes and foreign keys
        op.create_index(
            op.f(f"ix_{table_name}_consent_id_fk"),
            table_name,
            ["consent_id_fk"],
            unique=False,
        )
        op.create_index(
            op.f(f"ix_{table_name}_data_connection_id_fk"),
            table_name,
            ["data_connection_id_fk"],
            unique=False,
        )

        # Note: Alembic's create_foreign_key requires the constraint name.
        op.create_foreign_key(
            f"{table_name}_dataconnection_fk",
            table_name,
            "dataconnections",
            ["data_connection_id_fk"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            f"{table_name}_consent_fk",
            table_name,
            "consents",
            ["consent_id_fk"],
            ["id"],
            ondelete="SET NULL",
        )

        # Backfill ingestion_mode
        op.execute(
            f"UPDATE {table_name} SET ingestion_mode = 'SEEDED_PROTOTYPE' WHERE ingestion_mode IS NULL"
        )

        # Enforce non-null
        op.alter_column(
            table_name, "ingestion_mode", existing_type=sa.String(), nullable=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in EVIDENCE_TABLES:
        op.drop_constraint(
            f"{table_name}_dataconnection_fk", table_name, type_="foreignkey"
        )
        op.drop_constraint(f"{table_name}_consent_fk", table_name, type_="foreignkey")
        op.drop_index(
            op.f(f"ix_{table_name}_data_connection_id_fk"), table_name=table_name
        )
        op.drop_index(op.f(f"ix_{table_name}_consent_id_fk"), table_name=table_name)
        op.drop_column(table_name, "ingestion_mode")
        op.drop_column(table_name, "data_connection_id_fk")
        op.drop_column(table_name, "consent_id_fk")
