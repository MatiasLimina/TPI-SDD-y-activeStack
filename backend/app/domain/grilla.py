"""Duración en la grilla de 5 minutos (DD-15): una sola fuente para turnos y prestaciones."""

GRILLA_MIN = 5
DURACION_MAX_MIN = 480

MENSAJE_DURACION_INVALIDA = (
    f"la duración debe ser múltiplo de {GRILLA_MIN} entre {GRILLA_MIN} y {DURACION_MAX_MIN} minutos"
)


def duracion_en_grilla(duracion_min: int) -> bool:
    """`True` si la duración está en (0, 480] y es múltiplo de 5."""
    return 0 < duracion_min <= DURACION_MAX_MIN and duracion_min % GRILLA_MIN == 0
