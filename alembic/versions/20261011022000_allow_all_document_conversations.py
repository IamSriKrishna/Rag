"""Allow conversations that search all documents.

Revision ID: 20261011022000
Revises: 20261011014500
Create Date: 2026-10-11 02:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20261011022000"
down_revision = "20261011014500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "conversations",
        "document_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "conversations",
        "document_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
