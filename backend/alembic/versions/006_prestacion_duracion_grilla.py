"""prestacion: CHECK de la grilla de 5 minutos y del máximo de 480 (DD-15)

Revision ID: 006
Revises: 005
Create Date: 2026-11-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MULTIPLO = "ck_prestacion_duracion_min_multiplo_5"
_MAXIMA = "ck_prestacion_duracion_min_maxima"


def upgrade() -> None:
    # `op.f()` con el nombre completo: la convención de nombres no lo prefija otra vez.
    # `mod(...)` en vez de `%`: el `%` del texto SQL se confundiría con un marcador del driver.
    op.create_check_constraint(op.f(_MULTIPLO), "prestacion", "mod(duracion_min, 5) = 0")
    op.create_check_constraint(op.f(_MAXIMA), "prestacion", "duracion_min <= 480")


def downgrade() -> None:
    op.drop_constraint(op.f(_MAXIMA), "prestacion", type_="check")
    op.drop_constraint(op.f(_MULTIPLO), "prestacion", type_="check")
