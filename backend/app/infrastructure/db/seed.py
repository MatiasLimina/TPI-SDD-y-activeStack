"""Seed de desarrollo: catalogo minimo y usuarios con datos 100 % ficticios e idempotente.

Cada registro tiene un uuid fijo y se inserta con ``ON CONFLICT DO NOTHING``: re-ejecutar no
duplica, no falla y no pisa cambios hechos a mano (tampoco reactiva a un usuario desactivado ni
cambia su hash). Las contrasenas de los usuarios no viven en este codigo: se leen del entorno al
ejecutar (RN-CU-03) y se guardan solo como hash. Las funciones ``seed_*`` no hacen commit (lo
controla quien llama).
"""

import uuid
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import REPO_ROOT
from app.infrastructure.db.models import Paciente, Prestacion, Profesional, Sillon, Usuario
from app.infrastructure.db.session import get_engine
from app.infrastructure.security.contrasenas import Hasher, get_hasher

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


USUARIOS: list[Registro] = [
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000501"),
        "email": "recepcion@example.com",
        "rol": "recepcionista",
        "profesional_id": None,
        "variable": "SEED_RECEPCIONISTA_PASSWORD",
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000502"),
        "email": "ana.ficticia@example.com",
        "rol": "odontologo",
        "profesional_id": PROFESIONALES[0]["id"],
        "variable": "SEED_ODONTOLOGO_1_PASSWORD",
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000503"),
        "email": "bruno.inventado@example.com",
        "rol": "odontologo",
        "profesional_id": PROFESIONALES[1]["id"],
        "variable": "SEED_ODONTOLOGO_2_PASSWORD",
    },
]


class SeedSettings(BaseSettings):
    """Contrasenas de desarrollo del seed; opcionales: sin valor, ese usuario no se siembra.

    Lee el ``.env`` de la raiz (que trae variables ajenas, de ahi ``extra="ignore"``). Los tests
    lo construyen con ``_env_file=None`` y valores explicitos para no depender del ``.env`` local.
    """

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    SEED_RECEPCIONISTA_PASSWORD: str | None = None
    SEED_ODONTOLOGO_1_PASSWORD: str | None = None
    SEED_ODONTOLOGO_2_PASSWORD: str | None = None


def seed_catalogo(session: Session) -> None:
    """Inserta el catalogo ficticio; omite lo que ya existe (por id o clave natural)."""
    for modelo, registros in (
        (Profesional, PROFESIONALES),
        (Sillon, SILLONES),
        (Prestacion, PRESTACIONES),
        (Paciente, PACIENTES),
    ):
        session.execute(insert(modelo).values(registros).on_conflict_do_nothing())


def seed_usuarios(session: Session, contrasenas: SeedSettings, hasher: Hasher) -> None:
    """Inserta los usuarios cuya variable de contrasena esta definida y no vacia.

    Va despues del catalogo (FK a profesional). ``ON CONFLICT DO NOTHING`` sin target cubre id,
    email y el unico parcial por profesional: no pisa un usuario existente ni su hash.
    """
    for usuario in USUARIOS:
        contrasena = getattr(contrasenas, usuario["variable"])
        if not contrasena:
            continue
        session.execute(
            insert(Usuario)
            .values(
                id=usuario["id"],
                email=usuario["email"],
                password_hash=hasher.hash(contrasena),
                rol=usuario["rol"],
                profesional_id=usuario["profesional_id"],
            )
            .on_conflict_do_nothing()
        )


def main(contrasenas: SeedSettings | None = None, hasher: Hasher | None = None) -> None:
    """Punto de entrada: python -m app.infrastructure.db.seed (tras alembic upgrade head).

    Sin argumentos lee las contrasenas del entorno y usa el hasher de produccion; los tests
    inyectan una instancia aislada y un hasher barato.
    """
    contrasenas = contrasenas if contrasenas is not None else SeedSettings()
    hasher = hasher if hasher is not None else get_hasher()
    with Session(get_engine()) as session:
        seed_catalogo(session)
        seed_usuarios(session, contrasenas, hasher)
        session.commit()


if __name__ == "__main__":
    main()
