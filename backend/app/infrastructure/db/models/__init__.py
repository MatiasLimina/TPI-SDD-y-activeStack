"""Modelos ORM. Importar este paquete registra las tablas en Base.metadata."""

from app.infrastructure.db.models.paciente import Paciente
from app.infrastructure.db.models.prestacion import Prestacion
from app.infrastructure.db.models.profesional import Profesional
from app.infrastructure.db.models.sillon import Sillon
from app.infrastructure.db.models.turno import Turno
from app.infrastructure.db.models.usuario import Usuario

__all__ = ["Paciente", "Prestacion", "Profesional", "Sillon", "Turno", "Usuario"]
