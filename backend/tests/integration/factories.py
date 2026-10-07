"""Fábricas de catálogo ficticio para tests de turnos (solo datos inventados)."""

from dataclasses import dataclass
from itertools import count

from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon

_secuencia = count(1)


@dataclass
class Catalogo:
    profesionales: list[Profesional]
    sillones: list[Sillon]
    pacientes: list[Paciente]
    limpieza: Prestacion  # 45 min, requiere sillón
    consulta: Prestacion  # 30 min, no requiere sillón


def crear_catalogo(session: Session) -> Catalogo:
    """Dos profesionales, dos sillones, dos pacientes y dos prestaciones, con nombres únicos."""
    n = next(_secuencia)
    profesionales = [
        Profesional(nombre=f"Ana{n}", apellido="Ficticia"),
        Profesional(nombre=f"Beto{n}", apellido="Ficticio"),
    ]
    sillones = [Sillon(nombre=f"Sillon {n}-{i}") for i in (1, 2)]
    pacientes = [
        Paciente(
            nombre=f"Paula{n}",
            apellido="Ficticia",
            documento=f"FIC-{n}-1",
            telefono="+54 11 5555-0001",
        ),
        Paciente(
            nombre=f"Quique{n}",
            apellido="Ficticio",
            documento=f"FIC-{n}-2",
            telefono="+54 11 5555-0002",
        ),
    ]
    limpieza = Prestacion(nombre=f"Limpieza {n}", duracion_min=45)
    consulta = Prestacion(nombre=f"Consulta {n}", duracion_min=30, requiere_sillon=False)
    session.add_all([*profesionales, *sillones, *pacientes, limpieza, consulta])
    session.flush()
    return Catalogo(profesionales, sillones, pacientes, limpieza, consulta)
