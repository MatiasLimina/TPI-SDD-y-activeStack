"""horario_atencion: franjas de atención semanales por profesional

Revision ID: 007
Revises: 006
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# La fecha es arbitraria: solo sirve para armar un `tsrange` de horas de un mismo día
_RANGO = "tsrange(DATE '2000-01-03' + hora_inicio, DATE '2000-01-03' + hora_fin, '[)')"


def upgrade() -> None:
    op.create_table(
        "horario_atencion",
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
                name=op.f("fk_horario_atencion_profesional_id_profesional"),
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_horario_atencion")),
        sa.CheckConstraint(
            "dia_semana BETWEEN 0 AND 6", name=op.f("ck_horario_atencion_dia_semana_valido")
        ),
        sa.CheckConstraint(
            "hora_fin > hora_inicio", name=op.f("ck_horario_atencion_hora_fin_mayor")
        ),
        # `mod(...)` en vez de `%`: el `%` del texto SQL se confundiría con un marcador del driver
        sa.CheckConstraint(
            "mod(extract(epoch FROM hora_inicio)::int, 300) = 0 "
            "AND mod(extract(epoch FROM hora_fin)::int, 300) = 0",
            name=op.f("ck_horario_atencion_grilla"),
        ),
        postgresql.ExcludeConstraint(
            ("profesional_id", "="),
            ("dia_semana", "="),
            (sa.text(_RANGO), "&&"),
            name="horario_atencion_sin_superposicion",
            using="gist",
        ),
    )


def downgrade() -> None:
    op.drop_table("horario_atencion")
