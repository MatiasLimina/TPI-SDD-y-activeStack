"""bloqueo: franjas de la agenda de un profesional sin atención (RN-HB-02)

Revision ID: 010
Revises: 009
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bloqueo",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "profesional_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "profesional.id",
                name=op.f("fk_bloqueo_profesional_id_profesional"),
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column(
            "creado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "usuario.id", name=op.f("fk_bloqueo_creado_por_usuario"), ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bloqueo")),
        sa.CheckConstraint("fin > inicio", name=op.f("ck_bloqueo_fin_mayor")),
        sa.CheckConstraint("btrim(motivo) <> ''", name=op.f("ck_bloqueo_motivo_no_vacio")),
    )
    op.create_index("ix_bloqueo_profesional_id_inicio", "bloqueo", ["profesional_id", "inicio"])


def downgrade() -> None:
    op.drop_table("bloqueo")
