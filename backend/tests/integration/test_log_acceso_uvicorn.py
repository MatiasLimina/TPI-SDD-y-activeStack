"""El log de acceso de un `uvicorn` real no registra el texto buscado en /pacientes (D18).

Levanta `uvicorn app.main:app` en un subproceso, con los argumentos del `CMD` del `Dockerfile`
(salvo host y puerto), y lee su salida. A diferencia del test unitario del filtro, falla si
`uvicorn` cambia el formato de `record.args` y el filtro deja de actuar.
"""

import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import httpx
import pytest

from tests.conftest import BACKEND_DIR, SECRETO_TEST, get_test_database_url

ESPERA_S = 30
PROFESIONAL_ID = "00000000-0000-4000-8000-000000000101"


@dataclass
class ServidorUvicorn:
    url: str
    lineas: list[str] = field(default_factory=list)
    proceso: subprocess.Popen[str] | None = None

    def salida(self) -> str:
        return "".join(self.lineas)

    def esperar_linea(self, fragmento: str) -> str:
        """Espera hasta que la salida tenga una línea con `fragmento` y la devuelve."""
        limite = time.monotonic() + ESPERA_S
        while time.monotonic() < limite:
            for linea in list(self.lineas):
                if fragmento in linea:
                    return linea
            time.sleep(0.05)
        raise AssertionError(f"la salida de uvicorn no tuvo {fragmento!r}:\n{self.salida()}")


def _puerto_libre() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _leer(proceso: subprocess.Popen[str], lineas: list[str]) -> None:
    assert proceso.stdout is not None
    for linea in proceso.stdout:
        lineas.append(linea)


def _esperar_puerto(puerto: int, proceso: subprocess.Popen[str]) -> None:
    limite = time.monotonic() + ESPERA_S
    while time.monotonic() < limite:
        assert proceso.poll() is None, "uvicorn terminó antes de aceptar conexiones"
        with socket.socket() as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", puerto)) == 0:
                return
        time.sleep(0.1)
    raise AssertionError("uvicorn no abrió el puerto a tiempo")


@pytest.fixture(scope="module")
def servidor() -> Iterator[ServidorUvicorn]:
    puerto = _puerto_libre()
    entorno = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        # Valores explícitos de test: no dependen del `.env` ni tocan otra base
        "DATABASE_URL": get_test_database_url(),
        "JWT_SECRET": SECRETO_TEST,
    }
    proceso = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(puerto),
        ],
        cwd=BACKEND_DIR,
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    servidor = ServidorUvicorn(url=f"http://127.0.0.1:{puerto}", proceso=proceso)
    lector = threading.Thread(target=_leer, args=(proceso, servidor.lineas), daemon=True)
    lector.start()
    try:
        _esperar_puerto(puerto, proceso)
        yield servidor
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(timeout=10)
        lector.join(timeout=10)


def test_la_busqueda_de_pacientes_no_queda_en_el_log_de_acceso(
    servidor: ServidorUvicorn,
) -> None:
    respuesta = httpx.get(f"{servidor.url}/pacientes", params={"q": "FIC-0101", "limite": 10})

    assert respuesta.status_code == 401  # sin token: la petición igual llega al log de acceso
    linea = servidor.esperar_linea('"GET /pacientes HTTP/1.1"')
    assert "401" in linea
    assert "FIC-0101" not in servidor.salida()
    assert "limite" not in linea


def test_el_log_de_acceso_de_otras_rutas_conserva_la_query_string(
    servidor: ServidorUvicorn,
) -> None:
    respuesta = httpx.get(f"{servidor.url}/bloqueos", params={"profesional_id": PROFESIONAL_ID})

    assert respuesta.status_code == 401
    linea = servidor.esperar_linea("GET /bloqueos")
    assert f"/bloqueos?profesional_id={PROFESIONAL_ID}" in linea


def test_el_detalle_de_un_paciente_con_query_tampoco_la_registra(
    servidor: ServidorUvicorn,
) -> None:
    ruta = "/pacientes/3b241101-e2bb-4255-8caf-4136c566a962"

    respuesta = httpx.get(f"{servidor.url}{ruta}", params={"dato": "FIC-0202"})

    assert respuesta.status_code == 401
    servidor.esperar_linea(f'"GET {ruta} HTTP/1.1"')
    assert "FIC-0202" not in servidor.salida()
