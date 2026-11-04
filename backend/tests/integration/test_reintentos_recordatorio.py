"""Reintentos con backoff exponencial y estado fallido (emisor que falla, PostgreSQL real)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.notificaciones import MensajeRecordatorio
from tests.fakes import ColaEnMemoria, EmisorQueFalla, EmisorQueRegistra, RelojManual
from tests.integration.factories import Catalogo, crear_catalogo
from tests.integration.helpers_recordatorios import (
    PROGRAMADO_PARA,
    armar_worker,
    ciclo_a,
    crear_sin_programar,
    insertar_recordatorio,
    recordatorios_de,
)

T1 = datetime(2026, 10, 8, 13, 1, tzinfo=UTC)
T3 = datetime(2026, 10, 8, 13, 3, tzinfo=UTC)


@pytest.fixture
def catalogo(db_session: Session) -> Catalogo:
    return crear_catalogo(db_session)


def _pendiente_encolado(
    session: Session, catalogo: Catalogo, cola: ColaEnMemoria, *, intentos: int = 0
) -> tuple[Any, UUID]:
    turno = crear_sin_programar(session, catalogo)
    recordatorio_id = insertar_recordatorio(session, turno.id, intentos=intentos)
    cola.encolar(recordatorio_id, PROGRAMADO_PARA)
    return turno, recordatorio_id


def test_primer_intento_fallido_deja_pendiente_con_un_intento_y_reencola_a_1_minuto(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=10)
    turno, recordatorio_id = _pendiente_encolado(db_session, catalogo, cola)

    ciclo_a(armar_worker(db_session, cola, emisor, reloj), reloj, PROGRAMADO_PARA)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("pendiente", 1)
    assert fila["programado_para"] == T1
    assert cola.elementos == {recordatorio_id: T1}
    assert emisor.invocaciones == 1


def test_segundo_intento_fallido_reencola_a_2_minutos(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=10)
    turno, recordatorio_id = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor, reloj)
    ciclo_a(worker, reloj, PROGRAMADO_PARA)

    ciclo_a(worker, reloj, T1)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("pendiente", 2)
    assert fila["programado_para"] == T3
    assert cola.elementos == {recordatorio_id: T3}


def test_tercer_intento_fallido_deja_fallido_sin_reencolar_con_tres_invocaciones(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=10)
    turno, _ = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor, reloj)
    ciclo_a(worker, reloj, PROGRAMADO_PARA)
    ciclo_a(worker, reloj, T1)

    ciclo_a(worker, reloj, T3)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("fallido", 3)
    assert fila["programado_para"] == T3
    assert cola.elementos == {}
    assert emisor.invocaciones == 3
    assert ciclo_a(worker, reloj, datetime(2026, 10, 9, 13, 0, tzinfo=UTC)) == 0
    assert emisor.invocaciones == 3


def test_falla_y_despues_exito_deja_enviado_con_dos_intentos(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=1)
    turno, _ = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor, reloj)

    ciclo_a(worker, reloj, PROGRAMADO_PARA)
    ciclo_a(worker, reloj, T1)

    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("enviado", 2)
    assert cola.elementos == {}
    assert len(emisor.enviados) == 1


def test_el_reintento_no_se_entrega_antes_de_su_vencimiento(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola, emisor = ColaEnMemoria(), EmisorQueFalla(fallas=1)
    turno, _ = _pendiente_encolado(db_session, catalogo, cola)
    worker = armar_worker(db_session, cola, emisor, reloj)
    ciclo_a(worker, reloj, PROGRAMADO_PARA)

    procesados = ciclo_a(worker, reloj, datetime(2026, 10, 8, 13, 0, 59, tzinfo=UTC))

    assert procesados == 0
    assert emisor.invocaciones == 1
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["estado"], fila["intentos"]) == ("pendiente", 1)


def test_un_error_que_no_viene_del_emisor_se_propaga_y_deja_el_recordatorio_intacto(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola = ColaEnMemoria()
    # Un pendiente con 3 intentos es un dato anómalo que desde la 009 la base ya rechaza. Para
    # provocar un error de la base ajeno al emisor se quita ese CHECK dentro de la transacción
    # del test (el DDL de PostgreSQL es transaccional y se revierte al terminar).
    db_session.execute(
        text("ALTER TABLE recordatorio DROP CONSTRAINT ck_recordatorio_pendiente_intentos")
    )
    turno, recordatorio_id = _pendiente_encolado(db_session, catalogo, cola, intentos=3)
    db_session.commit()
    worker = armar_worker(db_session, cola, EmisorQueFalla(fallas=10), reloj)

    with pytest.raises(IntegrityError) as excinfo:
        ciclo_a(worker, reloj, PROGRAMADO_PARA)

    assert excinfo.value.orig.diag.constraint_name == "ck_recordatorio_intentos_rango"  # type: ignore[union-attr]
    (fila,) = recordatorios_de(db_session, turno.id)
    assert (fila["id"], fila["estado"], fila["intentos"]) == (recordatorio_id, "pendiente", 3)


def test_un_fallo_del_emisor_no_impide_procesar_el_resto_del_ciclo(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola = ColaEnMemoria()
    turno_a, _ = _pendiente_encolado(db_session, catalogo, cola)
    otro = crear_sin_programar(
        db_session,
        catalogo,
        datetime(2026, 10, 9, 15, 0, tzinfo=UTC),
        paciente=1,
    )
    otro_id = insertar_recordatorio(db_session, otro.id)
    cola.encolar(otro_id, PROGRAMADO_PARA.replace(minute=1))
    emisor = EmisorQueFalla(fallas=1)

    ciclo_a(armar_worker(db_session, cola, emisor, reloj), reloj, PROGRAMADO_PARA.replace(minute=5))

    (fila_a,) = recordatorios_de(db_session, turno_a.id)
    (fila_otro,) = recordatorios_de(db_session, otro.id)
    assert (fila_a["estado"], fila_a["intentos"]) == ("pendiente", 1)
    assert (fila_otro["estado"], fila_otro["intentos"]) == ("enviado", 1)


class EmisorQueTardaYFalla(EmisorQueRegistra):
    """Envía bien salvo a `falla_con`: con ese avanza el reloj `demora` y falla."""

    def __init__(self, reloj: RelojManual, demora: timedelta, falla_con: UUID) -> None:
        super().__init__()
        self._reloj = reloj
        self._demora = demora
        self._falla_con = falla_con

    def enviar(self, mensaje: MensajeRecordatorio) -> None:
        if mensaje.recordatorio_id == self._falla_con:
            self.invocaciones += 1
            self._reloj.avanzar(self._demora)
            raise RuntimeError("fallo de envío tras una demora (doble de test)")
        super().enviar(mensaje)


def test_la_espera_se_cuenta_desde_el_momento_de_la_falla_y_no_desde_el_inicio_del_ciclo(
    db_session: Session, catalogo: Catalogo
) -> None:
    reloj = RelojManual(PROGRAMADO_PARA)
    cola = ColaEnMemoria()
    turno_1, r1 = _pendiente_encolado(db_session, catalogo, cola)
    turno_2 = crear_sin_programar(
        db_session, catalogo, datetime(2026, 10, 9, 15, 0, tzinfo=UTC), paciente=1
    )
    r2 = insertar_recordatorio(db_session, turno_2.id)
    cola.encolar(r2, PROGRAMADO_PARA)
    emisor = EmisorQueTardaYFalla(reloj, timedelta(seconds=40), falla_con=r2)

    ciclo_a(armar_worker(db_session, cola, emisor, reloj), reloj, PROGRAMADO_PARA)

    esperado = PROGRAMADO_PARA + timedelta(minutes=1, seconds=40)
    (fila_1,) = recordatorios_de(db_session, turno_1.id)
    (fila_2,) = recordatorios_de(db_session, turno_2.id)
    assert (fila_1["id"], fila_1["estado"], fila_1["intentos"]) == (r1, "enviado", 1)
    assert (fila_2["estado"], fila_2["intentos"]) == ("pendiente", 1)
    assert fila_2["programado_para"] == esperado
    assert cola.elementos == {r2: esperado}
