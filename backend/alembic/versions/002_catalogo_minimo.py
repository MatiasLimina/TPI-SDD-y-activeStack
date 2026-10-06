"""catalogo minimo: profesional, sillon, prestacion, paciente

Revision ID: 002
Revises: 001
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column[postgresql.UUID]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def _activo(nombre: str) -> sa.Column[bool]:
    return sa.Column(nombre, sa.Boolean(), server_default=sa.text("true"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "profesional",
        _id(),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("apellido", sa.String(100), nullable=False),
        sa.Column("matricula", sa.String(30), nullable=True),
        _activo("activo"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profesional")),
        sa.UniqueConstraint("matricula", name=op.f("uq_profesional_matricula")),
    )
    op.create_table(
        "sillon",
        _id(),
        sa.Column("nombre", sa.String(50), nullable=False),
        _activo("activo"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sillon")),
        sa.UniqueConstraint("nombre", name=op.f("uq_sillon_nombre")),
    )
    op.create_table(
        "prestacion",
        _id(),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column("requiere_sillon", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _activo("activa"),
        *_timestamps(),
        sa.CheckConstraint("duracion_min > 0", name="duracion_min_positiva"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prestacion")),
        sa.UniqueConstraint("nombre", name=op.f("uq_prestacion_nombre")),
    )
    op.create_table(
        "paciente",
        _id(),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("apellido", sa.String(100), nullable=False),
        sa.Column("documento", sa.String(20), nullable=False),
        sa.Column("telefono", sa.String(30), nullable=False),
        sa.Column("email", sa.String(254), nullable=True),
        _activo("activo"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paciente")),
        sa.UniqueConstraint("documento", name=op.f("uq_paciente_documento")),
    )


def downgrade() -> None:
    op.drop_table("paciente")
    op.drop_table("prestacion")
    op.drop_table("sillon")
    op.drop_table("profesional")
