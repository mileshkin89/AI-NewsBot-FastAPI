"""simhash nullable for parser-created items

Revision ID: c6e3b2d09f4b
Revises: b5f2a1c08e3a
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6e3b2d09f4b"
down_revision: Union[str, Sequence[str], None] = "b5f2a1c08e3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "news_items",
        "simhash",
        existing_type=sa.BigInteger(),
        nullable=True,
        existing_server_default=sa.text("0"),
    )
    # Drop default so new rows can have NULL
    op.alter_column(
        "news_items",
        "simhash",
        existing_type=sa.BigInteger(),
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "news_items",
        "simhash",
        existing_type=sa.BigInteger(),
        nullable=False,
        server_default=sa.text("0"),
    )
