"""Filtro del log de acceso de uvicorn: quita la query string de las rutas de `/pacientes`.

`q` lleva nombres y documentos en la URL y uvicorn los registraría (DD-31 o). El filtro depende
del formato de `record.args` de `uvicorn.access`, `(cliente, método, ruta_con_query, versión,
estado)`: si cambia, no toca el registro (falla abierto) y lo detecta el test que levanta un
`uvicorn` real (`tests/integration/test_log_acceso_uvicorn.py`).
"""

import logging

LOGGER_ACCESO = "uvicorn.access"
_PREFIJO = "/pacientes"
_ARGUMENTOS_DE_ACCESO = 5


def _es_de_pacientes(ruta: str) -> bool:
    ruta = ruta.lower()
    return ruta == _PREFIJO or ruta.startswith(f"{_PREFIJO}/")


class FiltroLogAcceso(logging.Filter):
    """Nunca descarta un registro; solo recorta la query de las rutas de pacientes."""

    def filter(self, record: logging.LogRecord) -> bool:
        argumentos = record.args
        if not isinstance(argumentos, tuple) or len(argumentos) != _ARGUMENTOS_DE_ACCESO:
            return True
        ruta_con_query = argumentos[2]
        if not isinstance(ruta_con_query, str):
            return True
        ruta, _, _ = ruta_con_query.partition("?")
        if _es_de_pacientes(ruta):
            record.args = (*argumentos[:2], ruta, *argumentos[3:])
        return True


def instalar_filtro_log_acceso() -> None:
    """Agrega el filtro a `uvicorn.access` una sola vez, por más veces que se llame."""
    logger = logging.getLogger(LOGGER_ACCESO)
    if not any(isinstance(f, FiltroLogAcceso) for f in logger.filters):
        logger.addFilter(FiltroLogAcceso())
