"""Repositorio de pacientes contra PostgreSQL real: búsqueda, orden, paginación y turnos propios."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.domain.pacientes import terminos_busqueda
from app.infrastructure.db.models import Paciente, Profesional, Turno
from app.infrastructure.db.repositorio_pacientes import DEFINICION_PACIENTE, RepositorioPacientes
from tests.integration.factories import INICIO_BASE, Catalogo, crear_catalogo


def _paciente(
    session: Session,
    nombre: str,
    apellido: str,
    documento: str,
    *,
    activo: bool = True,
) -> Paciente:
    paciente = Paciente(
        nombre=nombre,
        apellido=apellido,
        documento=documento,
        telefono="+54 11 5555-0000",
        activo=activo,
    )
    session.add(paciente)
    session.flush()
    return paciente


def _buscar(
    session: Session, texto: str | None, *, limite: int = 100, desplazamiento: int = 0
) -> list[str]:
    repo = RepositorioPacientes(session)
    encontrados = repo.buscar(terminos_busqueda(texto), limite, desplazamiento)
    return [f"{p.nombre} {p.apellido}" for p in encontrados]


# --- Definición ---------------------------------------------------------------------------


def test_la_definicion_traduce_el_unique_del_documento() -> None:
    assert DEFINICION_PACIENTE.unicas == {"uq_paciente_documento": "documento"}
    assert DEFINICION_PACIENTE.flag == "activo"


# --- buscar: orden, inactivos y coincidencia parcial ---------------------------------------


def test_buscar_sin_terminos_lista_todos_ordenados_por_apellido_nombre_e_id(
    db_session: Session,
) -> None:
    _paciente(db_session, "Zoe", "Alfa", "FIC-1")
    _paciente(db_session, "Bruno", "Beta", "FIC-2")
    _paciente(db_session, "Ana", "Beta", "FIC-3", activo=False)

    assert _buscar(db_session, None) == ["Zoe Alfa", "Ana Beta", "Bruno Beta"]


def test_buscar_desempata_por_id_cuando_apellido_y_nombre_son_iguales(db_session: Session) -> None:
    ids = sorted(_paciente(db_session, "Igual", "Igual", f"FIC-{n}").id for n in range(4))

    repo = RepositorioPacientes(db_session)

    assert [p.id for p in repo.buscar([], 100, 0)] == ids


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("magin", ["Carla Imaginaria"]),  # parte del apellido
        ("dieg", ["Diego Supuesto"]),  # parte del nombre
        ("0202", ["Eva Tercera"]),  # parte del documento
        ("FIC-0101", ["Carla Imaginaria"]),
        ("zzz", []),
    ],
)
def test_buscar_coincide_por_subcadena_en_nombre_apellido_o_documento(
    db_session: Session, texto: str, esperado: list[str]
) -> None:
    _paciente(db_session, "Carla", "Imaginaria", "FIC-0101")
    _paciente(db_session, "Diego", "Supuesto", "FIC-0102")
    _paciente(db_session, "Eva", "Tercera", "FIC-0202")

    assert _buscar(db_session, texto) == esperado


def test_buscar_incluye_a_los_pacientes_desactivados(db_session: Session) -> None:
    _paciente(db_session, "Carla", "Imaginaria", "FIC-0101", activo=False)

    assert _buscar(db_session, "FIC-0101") == ["Carla Imaginaria"]


def test_buscar_exige_todos_los_terminos_aunque_esten_en_campos_distintos(
    db_session: Session,
) -> None:
    _paciente(db_session, "Carla", "Imaginaria", "FIC-0101")
    _paciente(db_session, "Carla", "Supuesta", "FIC-0102")
    _paciente(db_session, "Diego", "Imaginario", "FIC-0103")

    assert _buscar(db_session, "imag carla") == ["Carla Imaginaria"]
    assert _buscar(db_session, "carla 0102") == ["Carla Supuesta"]
    assert _buscar(db_session, "imag carla 0103") == []


# --- buscar: mayúsculas y acentos en ambos sentidos ----------------------------------------


@pytest.mark.parametrize("texto", ["perez", "PÉREZ", "Pérez", "pérez"])
def test_buscar_ignora_acentos_y_mayusculas_del_texto_buscado(
    db_session: Session, texto: str
) -> None:
    _paciente(db_session, "Lucía", "Pérez", "FIC-0301")
    _paciente(db_session, "Otro", "Gomez", "FIC-0302")

    assert _buscar(db_session, texto) == ["Lucía Pérez"]


@pytest.mark.parametrize("texto", ["alvarez", "ALVAREZ", "álvarez", "Álvarez"])
def test_buscar_encuentra_apellidos_guardados_con_acento_en_mayuscula(
    db_session: Session, texto: str
) -> None:
    _paciente(db_session, "Mario", "ÁLVAREZ", "FIC-0401")

    assert _buscar(db_session, texto) == ["Mario ÁLVAREZ"]


def test_buscar_con_acento_encuentra_lo_guardado_sin_acento(db_session: Session) -> None:
    _paciente(db_session, "Tomas", "Nunez", "FIC-0501")

    assert _buscar(db_session, "Nuñez") == ["Tomas Nunez"]
    assert _buscar(db_session, "tomás") == ["Tomas Nunez"]


def test_buscar_pliega_la_enie_y_la_dieresis(db_session: Session) -> None:
    _paciente(db_session, "Tomás", "Nuñez", "FIC-0601")
    _paciente(db_session, "Pingüino", "Güemes", "FIC-0602")

    assert _buscar(db_session, "nunez") == ["Tomás Nuñez"]
    assert _buscar(db_session, "guemes pinguino") == ["Pingüino Güemes"]


# --- buscar: comodines, límite y desplazamiento --------------------------------------------


def test_buscar_toma_porcentaje_guion_bajo_y_barra_como_texto(db_session: Session) -> None:
    _paciente(db_session, "Uno", "Guion", "FIC-0101")
    _paciente(db_session, "Dos", "Guion", "FIC_0102")
    _paciente(db_session, "Tres", "Porciento", "100%-0103")
    _paciente(db_session, "Cuatro", "Barra", "A\\B-0104")

    assert _buscar(db_session, "%") == ["Tres Porciento"]
    assert _buscar(db_session, "FIC_") == ["Dos Guion"]
    assert _buscar(db_session, "_") == ["Dos Guion"]
    assert _buscar(db_session, "\\") == ["Cuatro Barra"]
    assert _buscar(db_session, "a\\b") == ["Cuatro Barra"]
    assert _buscar(db_session, "%%") == []


def test_buscar_comodines_sin_coincidencia_literal_no_traen_nada(db_session: Session) -> None:
    _paciente(db_session, "Uno", "Guion", "FIC-0101")

    assert _buscar(db_session, "%") == []
    assert _buscar(db_session, "\\") == []
    assert _buscar(db_session, "F_C") == []


def test_buscar_aplica_limite_y_desplazamiento_despues_del_orden(db_session: Session) -> None:
    for n, apellido in enumerate(["Echeverria", "Alvarez", "Dominguez", "Benitez", "Cabrera"]):
        _paciente(db_session, "Pepe", apellido, f"FIC-{n}")

    assert _buscar(db_session, None, limite=2) == ["Pepe Alvarez", "Pepe Benitez"]
    assert _buscar(db_session, None, limite=2, desplazamiento=2) == [
        "Pepe Cabrera",
        "Pepe Dominguez",
    ]
    assert _buscar(db_session, None, limite=2, desplazamiento=4) == ["Pepe Echeverria"]
    assert _buscar(db_session, None, limite=2, desplazamiento=10) == []


def test_buscar_pagina_sin_repetidos_ante_apellido_y_nombre_iguales(db_session: Session) -> None:
    creados = {_paciente(db_session, "Igual", "Igual", f"FIC-{n}").id for n in range(5)}
    repo = RepositorioPacientes(db_session)

    paginas = [repo.buscar([], 2, desplazamiento) for desplazamiento in (0, 2, 4)]

    assert [len(pagina) for pagina in paginas] == [2, 2, 1]
    vistos = [p.id for pagina in paginas for p in pagina]
    assert len(vistos) == 5
    assert set(vistos) == creados


def test_buscar_pagina_sobre_el_resultado_filtrado(db_session: Session) -> None:
    for n in range(3):
        _paciente(db_session, f"Imag{n}", "Imaginaria", f"FIC-I{n}")
    for n in range(2):
        _paciente(db_session, f"Sup{n}", "Supuesto", f"FIC-S{n}")

    assert _buscar(db_session, "imaginaria", limite=2, desplazamiento=2) == ["Imag2 Imaginaria"]


# --- tiene_turno_de ------------------------------------------------------------------------


def test_tiene_turno_de_es_verdadero_con_un_turno_programado_del_profesional(
    db_session: Session,
) -> None:
    catalogo = crear_catalogo(db_session)
    paciente, otro = catalogo.pacientes
    profesional = catalogo.profesionales[0]
    _turno(db_session, catalogo, paciente=paciente, profesional=profesional)

    repo = RepositorioPacientes(db_session)

    assert repo.tiene_turno_de(paciente.id, profesional.id) is True
    assert repo.tiene_turno_de(otro.id, profesional.id) is False


def test_tiene_turno_de_es_verdadero_con_un_turno_cancelado(db_session: Session) -> None:
    catalogo = crear_catalogo(db_session)
    paciente = catalogo.pacientes[0]
    profesional = catalogo.profesionales[0]
    turno = _turno(db_session, catalogo, paciente=paciente, profesional=profesional)
    turno.estado = "cancelado"
    db_session.flush()

    assert RepositorioPacientes(db_session).tiene_turno_de(paciente.id, profesional.id) is True


def test_tiene_turno_de_es_verdadero_con_un_turno_pasado(db_session: Session) -> None:
    catalogo = crear_catalogo(db_session)
    paciente = catalogo.pacientes[0]
    profesional = catalogo.profesionales[0]
    _turno(db_session, catalogo, paciente=paciente, profesional=profesional, dias=-400)

    assert RepositorioPacientes(db_session).tiene_turno_de(paciente.id, profesional.id) is True


def test_tiene_turno_de_es_falso_si_los_turnos_son_solo_de_otro_profesional(
    db_session: Session,
) -> None:
    catalogo = crear_catalogo(db_session)
    paciente = catalogo.pacientes[0]
    propio, ajeno = catalogo.profesionales
    _turno(db_session, catalogo, paciente=paciente, profesional=ajeno)

    repo = RepositorioPacientes(db_session)

    assert repo.tiene_turno_de(paciente.id, propio.id) is False
    assert repo.tiene_turno_de(paciente.id, ajeno.id) is True


def test_tiene_turno_de_es_falso_sin_turnos_o_con_un_id_inexistente(db_session: Session) -> None:
    catalogo = crear_catalogo(db_session)
    profesional = catalogo.profesionales[0]
    repo = RepositorioPacientes(db_session)

    assert repo.tiene_turno_de(catalogo.pacientes[0].id, profesional.id) is False
    assert repo.tiene_turno_de(uuid4(), profesional.id) is False


def _turno(
    session: Session,
    catalogo: Catalogo,
    *,
    paciente: Paciente,
    profesional: Profesional,
    dias: int = 0,
) -> Turno:
    inicio = INICIO_BASE + timedelta(days=dias)
    turno = Turno(
        profesional_id=profesional.id,
        sillon_id=catalogo.sillones[0].id,
        paciente_id=paciente.id,
        prestacion_id=catalogo.limpieza.id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=45),
        duracion_min=45,
    )
    session.add(turno)
    session.flush()
    return turno
