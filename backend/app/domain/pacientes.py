"""Reglas de dominio de pacientes: búsqueda y email. Sin base de datos ni HTTP."""

import unicodedata

# Tabla única de plegado (DD-31 f): se aplica en SQL con `translate` y en Python a cada término.
# Cubre vocales con acento o diéresis y la `ñ`, en mayúscula y minúscula; después va `lower`.
CARACTERES_CON_ACENTO = "áéíóúüñÁÉÍÓÚÜÑ"
CARACTERES_SIN_ACENTO = "aeiouunAEIOUUN"
_PLEGADO = str.maketrans(CARACTERES_CON_ACENTO, CARACTERES_SIN_ACENTO)

MENSAJE_PACIENTE_AJENO = "Solo podés consultar pacientes de tus turnos"


class PacienteAjenoError(Exception):
    """Un odontólogo pidió un paciente sin turnos de su profesional, exista o no (403)."""

    def __init__(self, mensaje: str = MENSAJE_PACIENTE_AJENO) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


def plegar(texto: str) -> str:
    """Texto sin acentos ni mayúsculas, con la misma tabla que usa la consulta SQL."""
    return unicodedata.normalize("NFC", texto).translate(_PLEGADO).lower()


def email_valido(email: str) -> bool:
    """Chequeo mínimo (DD-31 m): una sola `@`, texto a ambos lados y ningún espacio en blanco."""
    local, arroba, dominio = email.partition("@")
    if not arroba or not local or not dominio or "@" in dominio:
        return False
    return not any(caracter.isspace() for caracter in email)


def terminos_busqueda(texto: str | None) -> list[str]:
    """Separa `q` en términos por los espacios y pliega cada uno; sin texto, lista vacía."""
    if not texto:
        return []
    return [plegar(termino) for termino in texto.split()]
