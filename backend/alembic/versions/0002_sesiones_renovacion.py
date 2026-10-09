"""Sesiones revocables para access/refresh tokens."""

import sqlalchemy as sa
from alembic import op

revision = "0002_sesiones_renovacion"
down_revision = "0001_linea_base"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sesiones_renovacion",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("sesiones_renovacion")
