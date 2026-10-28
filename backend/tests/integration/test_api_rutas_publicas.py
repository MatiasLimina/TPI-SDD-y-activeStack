"""Rutas públicas: la protección es por ruta, no global (DD-24)."""

import pytest
from fastapi.testclient import TestClient


def test_health_responde_200_sin_encabezado_authorization(cliente_anonimo: TestClient) -> None:
    respuesta = cliente_anonimo.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok", "database": "ok"}


@pytest.mark.parametrize(
    "authorization",
    ["Bearer no-es-un-jwt", "Basic dXN1YXJpbzpjbGF2ZQ==", "Bearer "],
    ids=["bearer-basura", "esquema-basic", "bearer-vacio"],
)
def test_health_ignora_un_authorization_invalido(
    cliente_anonimo: TestClient, authorization: str
) -> None:
    respuesta = cliente_anonimo.get("/health", headers={"Authorization": authorization})

    assert respuesta.status_code == 200


def test_ruta_inexistente_sin_token_responde_404_y_no_401(cliente_anonimo: TestClient) -> None:
    respuesta = cliente_anonimo.get("/no-existe")

    assert respuesta.status_code == 404
