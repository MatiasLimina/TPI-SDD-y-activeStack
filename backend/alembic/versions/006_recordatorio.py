"""recordatorio: recordatorios previos a los turnos, con integridad en la base

Revision ID: 006
Revises: 005
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PENDIENTE = "estado = 'pendiente'"


def upgrade() -> None:
    op.create_table(
        "recordatorio",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "turno_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "turno.id", name=op.f("fk_recordatorio_turno_id_turno"), ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column("programado_para", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(20), server_default="pendiente", nullable=False),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("intentos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recordatorio")),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'enviado', 'fallido', 'cancelado')",
            name=op.f("ck_recordatorio_estado_valido"),
        ),
        sa.CheckConstraint("canal IN ('mock')", name=op.f("ck_recordatorio_canal_valido")),
        sa.CheckConstraint("intentos BETWEEN 0 AND 3", name=op.f("ck_recordatorio_intentos_rango")),
        sa.CheckConstraint(
            "(estado <> 'fallido' OR intentos = 3) AND (estado <> 'enviado' OR intentos >= 1)",
            name=op.f("ck_recordatorio_intentos_segun_estado"),
        ),
    )
    op.create_index(
        "ux_recordatorio_turno_pendiente",
        "recordatorio",
        ["turno_id"],
        unique=True,
        postgresql_where=sa.text(_PENDIENTE),
    )
    op.create_index("ix_recordatorio_turno_id", "recordatorio", ["turno_id"])
    op.create_index(
        "ix_recordatorio_pendiente_programado_para",
        "recordatorio",
        ["programado_para"],
        postgresql_where=sa.text(_PENDIENTE),
    )


def downgrade() -> None:
    op.drop_index("ix_recordatorio_pendiente_programado_para", table_name="recordatorio")
    op.drop_index("ix_recordatorio_turno_id", table_name="recordatorio")
    op.drop_index("ux_recordatorio_turno_pendiente", table_name="recordatorio")
    op.drop_table("recordatorio")
