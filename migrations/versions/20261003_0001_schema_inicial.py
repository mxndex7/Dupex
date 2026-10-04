"""schema inicial: usuários e duplicatas

Revision ID: 0001
Revises:
Create Date: 2026-10-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index("ix_users_username", ["username"], unique=True)

    op.create_table(
        "duplicatas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(length=30), nullable=False),
        sa.Column("valor_centavos", sa.Integer(), nullable=False),
        sa.Column("emitente", sa.String(length=120), nullable=False),
        sa.Column("sacado", sa.String(length=120), nullable=False),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('emitida', 'aceita', 'liquidada', 'cancelada')", name="ck_duplicata_status"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "numero", name="uq_duplicata_owner_numero"),
    )
    with op.batch_alter_table("duplicatas") as batch_op:
        batch_op.create_index("ix_duplicata_owner_status", ["owner_id", "status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("duplicatas") as batch_op:
        batch_op.drop_index("ix_duplicata_owner_status")
    op.drop_table("duplicatas")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_username")
    op.drop_table("users")
