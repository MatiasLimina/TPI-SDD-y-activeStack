"""Acceso a datos de usuarios: búsqueda por email y actualización del hash."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Profesional, Usuario


class RepositorioUsuarios:
    def __init__(self, session: Session) -> None:
        self._session = session

    def por_email(self, email: str) -> Usuario | None:
        """Busca por email ya normalizado (activo o inactivo)."""
        return self._session.scalars(select(Usuario).where(Usuario.email == email)).one_or_none()

    def por_id(self, usuario_id: UUID) -> Usuario | None:
        """Busca por id (activo o inactivo); `None` si no existe."""
        return self._session.get(Usuario, usuario_id)

    def profesional_por_id(self, profesional_id: UUID) -> Profesional | None:
        """Busca un profesional (activo o inactivo); `None` si no existe."""
        return self._session.get(Profesional, profesional_id)

    def activo_de_profesional(self, profesional_id: UUID) -> Usuario | None:
        """El usuario activo asociado al profesional, si lo hay (a lo sumo uno, por la base)."""
        return self._session.scalars(
            select(Usuario).where(Usuario.profesional_id == profesional_id, Usuario.activo)
        ).one_or_none()

    def agregar(self, usuario: Usuario) -> None:
        """Inserta y envía a la base (sin commit): las restricciones saltan acá."""
        self._session.add(usuario)
        self._session.flush()

    def actualizar_hash(self, usuario_id: UUID, password_hash: str) -> None:
        self._session.execute(
            update(Usuario).where(Usuario.id == usuario_id).values(password_hash=password_hash)
        )

    def commit(self) -> None:
        self._session.commit()
