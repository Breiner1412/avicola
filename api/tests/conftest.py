"""Configuracion de las pruebas: usan la misma base de datos de desarrollo."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENTORNO", "pruebas")

from app.main import app  # noqa: E402
from app.core.config import config  # noqa: E402

API = "/api/v1"


@pytest.fixture(scope="session")
def cliente():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def token_plataforma(cliente):
    respuesta = cliente.post(
        f"{API}/auth/login",
        json={"email": config.admin_email, "clave": config.admin_password},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["token"]


def cabeceras(token: str, finca_id: int | None = None) -> dict[str, str]:
    datos = {"Authorization": f"Bearer {token}"}
    if finca_id is not None:
        datos["X-Finca-Id"] = str(finca_id)
    return datos


def unico(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:8]}"
