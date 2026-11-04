"""recordatorio: un pendiente no puede haber agotado los 3 intentos

Revision ID: 009
Revises: 008
Create Date: 2026-11-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHECK = "ck_recordatorio_pendiente_intentos"


def upgrade() -> None:
    op.create_check_constraint(
        op.f(_CHECK), "recordatorio", "estado <> 'pendiente' OR intentos < 3"
    )


def downgrade() -> None:
    op.drop_constraint(op.f(_CHECK), "recordatorio", type_="check")
