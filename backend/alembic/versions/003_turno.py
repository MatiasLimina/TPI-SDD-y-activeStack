"""turno: agenda con exclusion por profesional, sillon y paciente

Revision ID: 003
Revises: 002
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVO = "estado <> 'cancelado'"


def _fk(columna: str, tabla: str, nullable: bool) -> sa.Column[postgresql.UUID]:
    return sa.Column(
        columna,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey(f"{tabla}.id", name=op.f(f"fk_turno_{columna}_{tabla}"), ondelete="RESTRICT"),
        nullable=nullable,
    )


def upgrade() -> None:
    op.create_table(
        "turno",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        _fk("profesional_id", "profesional", nullable=False),
        _fk("paciente_id", "paciente", nullable=False),
        _fk("prestacion_id", "prestacion", nullable=False),
        _fk("sillon_id", "sillon", nullable=True),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), server_default="programado", nullable=False),
        sa.Column("motivo_cancelacion", sa.String(255), nullable=True),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_turno")),
        sa.CheckConstraint(
            "estado IN ('programado', 'cancelado')", name=op.f("ck_turno_estado_valido")
        ),
        sa.CheckConstraint("fin > inicio", name=op.f("ck_turno_fin_mayor")),
        postgresql.ExcludeConstraint(
            ("profesional_id", "="),
            (sa.text("tstzrange(inicio, fin, '[)')"), "&&"),
            name="turno_sin_solape_profesional",
            using="gist",
            where=sa.text(_ACTIVO),
        ),
        postgresql.ExcludeConstraint(
            ("sillon_id", "="),
            (sa.text("tstzrange(inicio, fin, '[)')"), "&&"),
            name="turno_sin_solape_sillon",
            using="gist",
            where=sa.text(f"{_ACTIVO} AND sillon_id IS NOT NULL"),
        ),
        postgresql.ExcludeConstraint(
            ("paciente_id", "="),
            (sa.text("tstzrange(inicio, fin, '[)')"), "&&"),
            name="turno_sin_solape_paciente",
            using="gist",
            where=sa.text(_ACTIVO),
        ),
    )
    op.create_index("ix_turno_profesional_id_inicio", "turno", ["profesional_id", "inicio"])
    op.create_index("ix_turno_sillon_id_inicio", "turno", ["sillon_id", "inicio"])


def downgrade() -> None:
    op.drop_table("turno")
