"""usuario: cuentas del sistema y FK de turno.creado_por

Revision ID: 004
Revises: 003
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column(
            "profesional_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "profesional.id",
                name=op.f("fk_usuario_profesional_id_profesional"),
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("email", name=op.f("uq_usuario_email")),
        sa.CheckConstraint(
            "rol IN ('recepcionista', 'odontologo')", name=op.f("ck_usuario_rol_valido")
        ),
        sa.CheckConstraint(
            "(rol = 'odontologo') = (profesional_id IS NOT NULL)",
            name=op.f("ck_usuario_profesional_segun_rol"),
        ),
        sa.CheckConstraint(
            "email = lower(btrim(email)) AND email <> ''",
            name=op.f("ck_usuario_email_normalizado"),
        ),
    )
    op.create_index("ix_usuario_profesional_id", "usuario", ["profesional_id"])
    op.create_index(
        "uq_usuario_profesional_activo",
        "usuario",
        ["profesional_id"],
        unique=True,
        postgresql_where=sa.text("activo"),
    )
    op.create_foreign_key(
        op.f("fk_turno_creado_por_usuario"),
        "turno",
        "usuario",
        ["creado_por"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_turno_creado_por", "turno", ["creado_por"])


def downgrade() -> None:
    op.drop_index("ix_turno_creado_por", table_name="turno")
    op.drop_constraint(op.f("fk_turno_creado_por_usuario"), "turno", type_="foreignkey")
    op.drop_table("usuario")
