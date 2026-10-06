"""Seed de desarrollo: catalogo minimo con datos 100 % ficticios e idempotente.

Cada registro tiene un uuid fijo y se inserta con ``ON CONFLICT DO NOTHING``: re-ejecutar no
duplica, no falla y no pisa cambios hechos a mano. No hace commit (lo controla quien llama).
"""

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon
from app.infrastructure.db.session import get_engine

Registro = dict[str, Any]

PROFESIONALES: list[Registro] = [
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000101"),
        "nombre": "Ana",
        "apellido": "Ficticia",
        "matricula": "MP-FIC-0001",
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000102"),
        "nombre": "Bruno",
        "apellido": "Inventado",
        "matricula": "MP-FIC-0002",
    },
]

SILLONES: list[Registro] = [
    {"id": uuid.UUID("00000000-0000-4000-8000-000000000201"), "nombre": "Sillón 1"},
    {"id": uuid.UUID("00000000-0000-4000-8000-000000000202"), "nombre": "Sillón 2"},
]

PRESTACIONES: list[Registro] = [
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000301"),
        "nombre": "Consulta",
        "duracion_min": 30,
        "requiere_sillon": False,
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000302"),
        "nombre": "Control",
        "duracion_min": 20,
        "requiere_sillon": False,
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000303"),
        "nombre": "Limpieza",
        "duracion_min": 45,
        "requiere_sillon": True,
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000304"),
        "nombre": "Conservadora",
        "duracion_min": 60,
        "requiere_sillon": True,
    },
]

PACIENTES: list[Registro] = [
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000401"),
        "nombre": "Carla",
        "apellido": "Imaginaria",
        "documento": "FIC-0001",
        "telefono": "+54 11 5555-0001",
        "email": "carla.imaginaria@example.com",
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000402"),
        "nombre": "Diego",
        "apellido": "Supuesto",
        "documento": "FIC-0002",
        "telefono": "+54 11 5555-0002",
        "email": "diego.supuesto@example.com",
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000403"),
        "nombre": "Elena",
        "apellido": "Simulada",
        "documento": "FIC-0003",
        "telefono": "+54 11 5555-0003",
        "email": None,
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000404"),
        "nombre": "Fabian",
        "apellido": "Ejemplo",
        "documento": "FIC-0004",
        "telefono": "+54 11 5555-0004",
        "email": "fabian.ejemplo@example.com",
    },
]


def seed_catalogo(session: Session) -> None:
    """Inserta el catalogo ficticio; omite lo que ya existe (por id o clave natural)."""
    for modelo, registros in (
        (Profesional, PROFESIONALES),
        (Sillon, SILLONES),
        (Prestacion, PRESTACIONES),
        (Paciente, PACIENTES),
    ):
        session.execute(insert(modelo).values(registros).on_conflict_do_nothing())


def main() -> None:
    """Punto de entrada: python -m app.infrastructure.db.seed (tras alembic upgrade head)."""
    with Session(get_engine()) as session:
        seed_catalogo(session)
        session.commit()


if __name__ == "__main__":
    main()
