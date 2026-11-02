"""Repositorio genérico del catálogo contra PostgreSQL real (profesional, sillón, prestación)."""

from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.recursos import RecursoDuplicadoError, TipoRecurso
from app.infrastructure.db.models import Prestacion, Profesional, Sillon
from app.infrastructure.db.models.mixins import CatalogoMixin
from app.infrastructure.db.repositorio_recursos import (
    DEFINICION_PRESTACION,
    DEFINICION_PROFESIONAL,
    DEFINICION_SILLON,
    DefinicionRecurso,
    RepositorioRecursos,
)

DEFINICIONES = [
    pytest.param(
        DEFINICION_PROFESIONAL,
        lambda n: Profesional(nombre="Ana", apellido=n, matricula=f"MN-{n}"),
        "activo",
        id="profesional",
    ),
    pytest.param(DEFINICION_SILLON, lambda n: Sillon(nombre=f"Sillón {n}"), "activo", id="sillon"),
    pytest.param(
        DEFINICION_PRESTACION,
        lambda n: Prestacion(nombre=f"Prestación {n}", duracion_min=30),
        "activa",
        id="prestacion",
    ),
]


def _repo(session: Session, definicion: DefinicionRecurso) -> RepositorioRecursos:
    return RepositorioRecursos(session, definicion)


@pytest.mark.parametrize(("definicion", "fabrica", "flag"), DEFINICIONES)
def test_agregar_y_guardar_persiste_el_recurso_activo(
    db_session: Session,
    definicion: DefinicionRecurso,
    fabrica: Callable[[str], CatalogoMixin],
    flag: str,
) -> None:
    repo = _repo(db_session, definicion)
    entidad = fabrica("1")

    repo.agregar(entidad)
    repo.guardar()

    guardada = repo.obtener(entidad.id)
    assert guardada is entidad
    assert getattr(guardada, flag) is True
    assert definicion.flag == flag


@pytest.mark.parametrize(("definicion", "fabrica", "flag"), DEFINICIONES)
def test_obtener_devuelve_none_para_un_uuid_desconocido(
    db_session: Session,
    definicion: DefinicionRecurso,
    fabrica: Callable[[str], CatalogoMixin],
    flag: str,
) -> None:
    assert _repo(db_session, definicion).obtener(uuid4()) is None


@pytest.mark.parametrize(("definicion", "fabrica", "flag"), DEFINICIONES)
def test_obtener_para_actualizar_devuelve_la_fila_y_none_si_no_existe(
    db_session: Session,
    definicion: DefinicionRecurso,
    fabrica: Callable[[str], CatalogoMixin],
    flag: str,
) -> None:
    repo = _repo(db_session, definicion)
    entidad = fabrica("1")
    repo.agregar(entidad)
    repo.guardar()

    assert repo.obtener_para_actualizar(entidad.id) is entidad
    assert repo.obtener_para_actualizar(uuid4()) is None


def test_listar_profesionales_incluye_inactivos_ordenados_por_apellido_nombre_e_id(
    db_session: Session,
) -> None:
    repo = _repo(db_session, DEFINICION_PROFESIONAL)
    zoe = Profesional(nombre="Zoe", apellido="Alfa")
    ana = Profesional(nombre="Ana", apellido="Beta", activo=False)
    abel = Profesional(nombre="Abel", apellido="Beta")
    for profesional in (zoe, ana, abel):
        repo.agregar(profesional)
    repo.guardar()

    listado = repo.listar()

    assert [(p.apellido, p.nombre, p.activo) for p in listado] == [
        ("Alfa", "Zoe", True),
        ("Beta", "Abel", True),
        ("Beta", "Ana", False),
    ]


def test_listar_profesionales_desempata_por_id_cuando_coinciden_apellido_y_nombre(
    db_session: Session,
) -> None:
    repo = _repo(db_session, DEFINICION_PROFESIONAL)
    gemelos = [Profesional(nombre="Gil", apellido="Igual", matricula=f"MN-{i}") for i in range(3)]
    for gemelo in gemelos:
        repo.agregar(gemelo)
    repo.guardar()

    assert [p.id for p in repo.listar()] == sorted(g.id for g in gemelos)


def test_listar_sillones_incluye_inactivos_ordenados_por_nombre(db_session: Session) -> None:
    repo = _repo(db_session, DEFINICION_SILLON)
    repo.agregar(Sillon(nombre="Sillón 2"))
    repo.agregar(Sillon(nombre="Sillón 1", activo=False))
    repo.guardar()

    assert [(s.nombre, s.activo) for s in repo.listar()] == [
        ("Sillón 1", False),
        ("Sillón 2", True),
    ]


def test_listar_prestaciones_incluye_inactivas_ordenadas_por_nombre(db_session: Session) -> None:
    repo = _repo(db_session, DEFINICION_PRESTACION)
    repo.agregar(Prestacion(nombre="Limpieza", duracion_min=45))
    repo.agregar(Prestacion(nombre="Consulta", duracion_min=30, activa=False))
    repo.guardar()

    assert [(p.nombre, p.activa) for p in repo.listar()] == [
        ("Consulta", False),
        ("Limpieza", True),
    ]


def test_listar_devuelve_lista_vacia_sin_recursos(db_session: Session) -> None:
    assert _repo(db_session, DEFINICION_SILLON).listar() == []


# --- 5.2 traducción de duplicados --------------------------------------------------------


def test_guardar_traduce_nombre_de_sillon_repetido(db_session: Session) -> None:
    repo = _repo(db_session, DEFINICION_SILLON)
    repo.agregar(Sillon(nombre="Sillón 1"))
    repo.guardar()
    repo.agregar(Sillon(nombre="Sillón 1"))

    with pytest.raises(RecursoDuplicadoError) as excinfo:
        repo.guardar()

    assert excinfo.value.tipo is TipoRecurso.SILLON
    assert excinfo.value.campo == "nombre"


def test_guardar_traduce_nombre_de_prestacion_repetido(db_session: Session) -> None:
    repo = _repo(db_session, DEFINICION_PRESTACION)
    repo.agregar(Prestacion(nombre="Limpieza", duracion_min=45))
    repo.guardar()
    repo.agregar(Prestacion(nombre="Limpieza", duracion_min=30))

    with pytest.raises(RecursoDuplicadoError) as excinfo:
        repo.guardar()

    assert excinfo.value.tipo is TipoRecurso.PRESTACION
    assert excinfo.value.campo == "nombre"


def test_guardar_traduce_matricula_de_profesional_repetida(db_session: Session) -> None:
    repo = _repo(db_session, DEFINICION_PROFESIONAL)
    repo.agregar(Profesional(nombre="Ana", apellido="Ficticia", matricula="MN-0001"))
    repo.guardar()
    repo.agregar(Profesional(nombre="Bruno", apellido="Inventado", matricula="MN-0001"))

    with pytest.raises(RecursoDuplicadoError) as excinfo:
        repo.guardar()

    assert excinfo.value.tipo is TipoRecurso.PROFESIONAL
    assert excinfo.value.campo == "matricula"


def test_guardar_relanza_sin_traducir_una_violacion_de_otra_restriccion(
    db_session: Session,
) -> None:
    repo = _repo(db_session, DEFINICION_PRESTACION)
    repo.agregar(Prestacion(nombre="Fuera de grilla", duracion_min=7))

    with pytest.raises(IntegrityError) as excinfo:
        repo.guardar()

    assert "ck_prestacion_duracion_min_multiplo_5" in str(excinfo.value.orig)


def test_dos_profesionales_sin_matricula_no_son_duplicados(db_session: Session) -> None:
    repo = _repo(db_session, DEFINICION_PROFESIONAL)
    repo.agregar(Profesional(nombre="Ana", apellido="Ficticia"))
    repo.agregar(Profesional(nombre="Bruno", apellido="Inventado"))

    repo.guardar()

    total = db_session.execute(
        text("SELECT count(*) FROM profesional WHERE matricula IS NULL")
    ).scalar_one()
    assert total == 2


# --- modificar ---------------------------------------------------------------------------


def test_modificar_y_guardar_aplican_los_cambios_solo_enviados(db_session: Session) -> None:
    repo = _repo(db_session, DEFINICION_PROFESIONAL)
    ana = Profesional(nombre="Ana", apellido="Ficticia", matricula="MN-0001")
    repo.agregar(ana)
    repo.guardar()

    repo.modificar(ana, {"apellido": "Segunda"})
    repo.guardar()

    assert (ana.nombre, ana.apellido, ana.matricula) == ("Ana", "Segunda", "MN-0001")


def test_modificar_a_un_valor_repetido_se_traduce_y_la_sesion_sigue_usable(
    db_session: Session,
) -> None:
    repo = _repo(db_session, DEFINICION_SILLON)
    uno, dos = Sillon(nombre="Sillón 1"), Sillon(nombre="Sillón 2")
    repo.agregar(uno)
    repo.agregar(dos)
    repo.guardar()

    repo.modificar(dos, {"nombre": "Sillón 1"})
    with pytest.raises(RecursoDuplicadoError) as excinfo:
        repo.guardar()

    assert excinfo.value.campo == "nombre"
    db_session.expire_all()
    assert [s.nombre for s in repo.listar()] == ["Sillón 1", "Sillón 2"]
