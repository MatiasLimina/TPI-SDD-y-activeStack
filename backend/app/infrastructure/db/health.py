from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def check_database(session: Session) -> bool:
    """True si la base responde a un SELECT 1; False ante cualquier error de conexion."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
