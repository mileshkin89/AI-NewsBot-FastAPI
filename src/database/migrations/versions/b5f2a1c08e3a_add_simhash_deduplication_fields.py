"""add simhash, duplicate_of_id and indexes for deduplication

Revision ID: b5f2a1c08e3a
Revises: 4e0a14032101
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5f2a1c08e3a"
down_revision: Union[str, Sequence[str], None] = "4e0a14032101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "news_items",
        sa.Column("simhash", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "news_items",
        sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_news_items_duplicate_of_id",
        "news_items",
        "news_items",
        ["duplicate_of_id"],
        ["id"],
    )
    op.create_index(
        "ix_news_items_simhash",
        "news_items",
        ["simhash"],
        unique=False,
    )
    op.create_index(
        "ix_news_items_created_at",
        "news_items",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_news_items_created_at", table_name="news_items")
    op.drop_index("ix_news_items_simhash", table_name="news_items")
    op.drop_constraint(
        "fk_news_items_duplicate_of_id",
        "news_items",
        type_="foreignkey",
    )
    op.drop_column("news_items", "duplicate_of_id")
    op.drop_column("news_items", "simhash")
