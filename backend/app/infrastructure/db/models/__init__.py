"""Modelos ORM. Importar este paquete registra las tablas en Base.metadata."""

from app.infrastructure.db.models.paciente import Paciente
from app.infrastructure.db.models.prestacion import Prestacion
from app.infrastructure.db.models.profesional import Profesional
from app.infrastructure.db.models.sillon import Sillon

__all__ = ["Paciente", "Prestacion", "Profesional", "Sillon"]
