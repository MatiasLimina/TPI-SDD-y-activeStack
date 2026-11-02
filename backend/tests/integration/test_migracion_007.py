"""Migración 007: tabla horario_atencion con CHECKs, exclusión por profesional/día y FK CASCADE."""

from alembic import command
from sqlalchemy import create_engine, text

from tests.conftest import alembic_config

DIA = "ck_horario_atencion_dia_semana_valido"
FIN = "ck_horario_atencion_hora_fin_mayor"
GRILLA = "ck_horario_atencion_grilla"
EXCLUSION = "horario_atencion_sin_superposicion"


def _constraints(url: str) -> dict[str, tuple[str, str]]:
    """nombre -> (tipo, definición) de las restricciones de horario_atencion; {} si no existe."""
    scratch = create_engine(url)
    try:
        with scratch.connect() as connection:
            if connection.execute(text("SELECT to_regclass('horario_atencion')")).scalar() is None:
                return {}
            filas = connection.execute(
                text(
                    "SELECT conname, contype, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'horario_atencion'::regclass"
                )
            ).all()
        return {nombre: (tipo, definicion) for nombre, tipo, definicion in filas}
    finally:
        scratch.dispose()


def test_upgrade_head_crea_horario_atencion_con_sus_garantias(scratch_url: str) -> None:
    command.upgrade(alembic_config(scratch_url), "head")

    restricciones = _constraints(scratch_url)

    assert {DIA, FIN, GRILLA, EXCLUSION} <= set(restricciones)
    assert restricciones[DIA][0] == restricciones[FIN][0] == restricciones[GRILLA][0] == "c"
    assert "dia_semana >= 0" in restricciones[DIA][1]
    assert "hora_fin > hora_inicio" in restricciones[FIN][1]
    tipo, definicion = restricciones[EXCLUSION]
    assert tipo == "x"
    assert "profesional_id WITH =" in definicion
    assert "dia_semana WITH =" in definicion
    assert "&&" in definicion
    fks = [d for t, d in restricciones.values() if t == "f"]
    assert len(fks) == 1
    assert "REFERENCES profesional(id) ON DELETE CASCADE" in fks[0]


def test_downgrade_a_006_elimina_la_tabla_y_reupgrade_la_restaura(scratch_url: str) -> None:
    config = alembic_config(scratch_url)
    command.upgrade(config, "head")

    command.downgrade(config, "006")

    assert _constraints(scratch_url) == {}

    command.upgrade(config, "head")

    assert EXCLUSION in _constraints(scratch_url)
