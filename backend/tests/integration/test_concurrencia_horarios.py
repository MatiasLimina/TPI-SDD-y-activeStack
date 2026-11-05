"""Altas simultáneas de franjas superpuestas por HTTP, cada request en su propia conexión."""

import threading
from collections.abc import Iterator
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import get_emisor_tokens, get_hasher
from app.infrastructure.db.models import HorarioAtencion, Usuario
from app.infrastructure.db.session import get_session
from app.infrastructure.security.contrasenas import Hasher
from app.infrastructure.security.tokens import EmisorTokens
from app.main import create_app
from tests.integration.factories import Catalogo

LUNES = 0


def test_dos_altas_http_superpuestas_en_paralelo_dan_un_201_y_un_409(
    motor_concurrente: Engine,
    catalogo_commiteado_sin_horario: Catalogo,
    recepcionista_commiteada: Usuario,
    hasher_test: Hasher,
    emisor_test: EmisorTokens,
) -> None:
    profesional = catalogo_commiteado_sin_horario.profesionales[0]
    fabrica = sessionmaker(bind=motor_concurrente, expire_on_commit=False)
    app = create_app()

    def sesion_por_request() -> Iterator[Session]:
        with fabrica() as sesion:
            yield sesion

    app.dependency_overrides[get_session] = sesion_por_request
    app.dependency_overrides[get_hasher] = lambda: hasher_test
    app.dependency_overrides[get_emisor_tokens] = lambda: emisor_test
    encabezados = {"Authorization": f"Bearer {emisor_test.emitir(recepcionista_commiteada)}"}
    respuestas: list[Any] = []
    largada = threading.Barrier(2)

    def alta(hora_inicio: str, hora_fin: str) -> None:
        with TestClient(app, headers=encabezados) as cliente:
            largada.wait(timeout=10)
            respuestas.append(
                cliente.post(
                    f"/profesionales/{profesional.id}/horarios",
                    json={"dia_semana": LUNES, "hora_inicio": hora_inicio, "hora_fin": hora_fin},
                )
            )

    hilos = [
        threading.Thread(target=alta, args=("09:00", "13:00")),
        threading.Thread(target=alta, args=("12:00", "16:00")),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    assert sorted(r.status_code for r in respuestas) == [201, 409]
    rechazada = next(r for r in respuestas if r.status_code == 409)
    assert rechazada.json() == {"detail": {"codigo": "franja_superpuesta"}}
    with Session(motor_concurrente) as sesion:
        franjas = sesion.scalars(
            select(HorarioAtencion).where(
                HorarioAtencion.profesional_id == profesional.id,
                HorarioAtencion.dia_semana == LUNES,
            )
        ).all()
    assert len(franjas) == 1
