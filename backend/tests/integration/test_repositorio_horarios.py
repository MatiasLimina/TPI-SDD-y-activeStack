"""RepositorioHorarios contra PostgreSQL real."""

from datetime import time
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.horarios import Franja, FranjaSuperpuestaError
from app.infrastructure.db.models import HorarioAtencion, Profesional
from app.infrastructure.db.repositorio_horarios import RepositorioHorarios


@pytest.fixture
def profesionales(db_session: Session) -> list[Profesional]:
    lista = [Profesional(nombre=n, apellido="Ficticio") for n in ("Ana", "Beto")]
    db_session.add_all(lista)
    db_session.flush()
    return lista


@pytest.fixture
def repo(db_session: Session) -> RepositorioHorarios:
    return RepositorioHorarios(db_session)


def _nueva(p: Profesional, dia: int, inicio: time, fin: time) -> HorarioAtencion:
    return HorarioAtencion(profesional_id=p.id, dia_semana=dia, hora_inicio=inicio, hora_fin=fin)


def _cargar(repo: RepositorioHorarios, *franjas: HorarioAtencion) -> None:
    for franja in franjas:
        repo.agregar(franja)
    repo.guardar()


def test_bloquear_profesional_devuelve_none_para_un_uuid_desconocido(
    repo: RepositorioHorarios,
) -> None:
    assert repo.bloquear_profesional(uuid4()) is None


def test_bloquear_profesional_devuelve_el_profesional_existente(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    encontrado = repo.bloquear_profesional(profesionales[0].id)

    assert encontrado is not None
    assert encontrado.id == profesionales[0].id


def test_obtener_profesional_lee_sin_bloquear_y_devuelve_none_si_no_existe(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    assert repo.obtener_profesional(profesionales[1].id) is profesionales[1]
    assert repo.obtener_profesional(uuid4()) is None


def test_agregar_y_guardar_persiste_la_franja(
    repo: RepositorioHorarios, db_session: Session, profesionales: list[Profesional]
) -> None:
    franja = _nueva(profesionales[0], 0, time(9, 0), time(13, 0))

    _cargar(repo, franja)

    guardada = db_session.get(HorarioAtencion, franja.id)
    assert guardada is not None
    assert (guardada.dia_semana, guardada.hora_inicio, guardada.hora_fin) == (
        0,
        time(9, 0),
        time(13, 0),
    )


def test_listar_ordena_por_dia_y_hora_y_excluye_otros_profesionales(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    ana, beto = profesionales
    _cargar(
        repo,
        _nueva(ana, 1, time(9, 0), time(13, 0)),
        _nueva(ana, 0, time(14, 0), time(18, 0)),
        _nueva(ana, 0, time(9, 0), time(13, 0)),
        _nueva(beto, 0, time(9, 0), time(13, 0)),
    )

    listadas = repo.listar(ana.id)

    assert [(f.dia_semana, f.hora_inicio) for f in listadas] == [
        (0, time(9, 0)),
        (0, time(14, 0)),
        (1, time(9, 0)),
    ]
    assert all(f.profesional_id == ana.id for f in listadas)
    assert repo.listar(uuid4()) == []


def test_franjas_del_dia_devuelve_solo_las_del_dia_pedido(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    ana, beto = profesionales
    _cargar(
        repo,
        _nueva(ana, 3, time(14, 0), time(18, 0)),
        _nueva(ana, 3, time(9, 0), time(13, 0)),
        _nueva(ana, 4, time(9, 0), time(13, 0)),
        _nueva(beto, 3, time(8, 0), time(12, 0)),
    )

    assert repo.franjas_del_dia(ana.id, 3) == [
        Franja(3, time(9, 0), time(13, 0)),
        Franja(3, time(14, 0), time(18, 0)),
    ]
    assert repo.franjas_del_dia(ana.id, 5) == []


def test_obtener_devuelve_none_si_la_franja_es_de_otro_profesional(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    ana, beto = profesionales
    franja = _nueva(beto, 0, time(9, 0), time(13, 0))
    _cargar(repo, franja)

    assert repo.obtener(ana.id, franja.id) is None
    assert repo.obtener(beto.id, uuid4()) is None
    obtenida = repo.obtener(beto.id, franja.id)
    assert obtenida is not None
    assert obtenida.id == franja.id


def test_superpuestas_detecta_el_choque_e_ignora_a_la_propia_franja(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    ana, beto = profesionales
    propia = _nueva(ana, 0, time(9, 0), time(13, 0))
    otra = _nueva(ana, 0, time(14, 0), time(18, 0))
    _cargar(repo, propia, otra, _nueva(beto, 0, time(9, 0), time(13, 0)))
    achicada = Franja(0, time(10, 0), time(15, 0))

    assert {f.id for f in repo.superpuestas(ana.id, achicada, None)} == {propia.id, otra.id}
    assert {f.id for f in repo.superpuestas(ana.id, achicada, propia.id)} == {otra.id}
    assert repo.superpuestas(ana.id, Franja(0, time(13, 0), time(14, 0)), None) == []
    assert repo.superpuestas(ana.id, Franja(1, time(9, 0), time(13, 0)), None) == []


def test_modificar_aplica_los_cambios_al_guardar(
    repo: RepositorioHorarios, db_session: Session, profesionales: list[Profesional]
) -> None:
    franja = _nueva(profesionales[0], 0, time(9, 0), time(13, 0))
    _cargar(repo, franja)

    repo.modificar(franja, {"hora_fin": time(14, 0)})
    repo.guardar()

    db_session.expire(franja)
    assert franja.hora_fin == time(14, 0)


def test_eliminar_borra_la_franja(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    franja = _nueva(profesionales[0], 0, time(9, 0), time(13, 0))
    _cargar(repo, franja)

    repo.eliminar(franja)

    assert repo.listar(profesionales[0].id) == []


def test_guardar_traduce_la_exclusion_a_franja_superpuesta_y_deja_la_sesion_usable(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    ana = profesionales[0]
    _cargar(repo, _nueva(ana, 0, time(9, 0), time(13, 0)))
    repo.agregar(_nueva(ana, 0, time(12, 0), time(15, 0)))

    with pytest.raises(FranjaSuperpuestaError):
        repo.guardar()

    assert len(repo.listar(ana.id)) == 1


def test_guardar_relanza_cualquier_otra_violacion(
    repo: RepositorioHorarios, profesionales: list[Profesional]
) -> None:
    repo.agregar(_nueva(profesionales[0], 7, time(9, 0), time(13, 0)))

    with pytest.raises(IntegrityError):
        repo.guardar()
