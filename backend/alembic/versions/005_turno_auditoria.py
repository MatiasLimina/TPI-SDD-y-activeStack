"""turno_auditoria: registro append-only de cambios de turnos

Revision ID: 005
Revises: 004
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FUNCION = "turno_auditoria_inmutable"
_MENSAJE = "turno_auditoria es append-only"


def upgrade() -> None:
    op.create_table(
        "turno_auditoria",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "turno_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "turno.id", name=op.f("fk_turno_auditoria_turno_id_turno"), ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "usuario.id",
                name=op.f("fk_turno_auditoria_usuario_id_usuario"),
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("accion", sa.String(20), nullable=False),
        sa.Column("valores_previos", postgresql.JSONB(), nullable=True),
        sa.Column("valores_nuevos", postgresql.JSONB(), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_turno_auditoria")),
        sa.CheckConstraint(
            "accion IN ('crear', 'reprogramar', 'cancelar')",
            name=op.f("ck_turno_auditoria_accion_valida"),
        ),
        sa.CheckConstraint(
            "(accion = 'crear') = (valores_previos IS NULL)",
            name=op.f("ck_turno_auditoria_previos_segun_accion"),
        ),
    )
    op.create_index("ix_turno_auditoria_turno_id", "turno_auditoria", ["turno_id", "id"])
    op.create_index("ix_turno_auditoria_usuario_id", "turno_auditoria", ["usuario_id"])

    op.execute(
        f"""
        CREATE FUNCTION {_FUNCION}() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '{_MENSAJE}';
        END;
        $$
        """
    )
    op.execute(
        f"CREATE TRIGGER turno_auditoria_sin_modificar BEFORE UPDATE OR DELETE "
        f"ON turno_auditoria FOR EACH ROW EXECUTE FUNCTION {_FUNCION}()"
    )
    op.execute(
        f"CREATE TRIGGER turno_auditoria_sin_vaciar BEFORE TRUNCATE "
        f"ON turno_auditoria FOR EACH STATEMENT EXECUTE FUNCTION {_FUNCION}()"
    )


def downgrade() -> None:
    # DROP TABLE no dispara los triggers y se lleva consigo los dos triggers de la tabla
    op.drop_table("turno_auditoria")
    op.execute(f"DROP FUNCTION {_FUNCION}()")
