"""Topes generales de peticiones y Redis obligatorio en produccion."""

import pytest

from app.core import limites
from tests.conftest import API, cabeceras


def test_demasiados_cambios_seguidos_se_frenan(cliente, token_plataforma, monkeypatch):
    monkeypatch.setattr(limites.escrituras, "maximo", 3)
    codigos = [
        cliente.post(f"{API}/galpones", headers=cabeceras(token_plataforma), json={}).status_code for _ in range(4)
    ]
    assert codigos[:3] == [422, 422, 422]
    assert codigos[3] == 429
    # Las consultas no cuentan
    assert cliente.get(f"{API}/auth/yo", headers=cabeceras(token_plataforma)).status_code == 200


def test_en_produccion_sin_redis_no_arranca(monkeypatch):
    from fastapi.testclient import TestClient

    from app.core import cache
    from app.core.config import config
    from app.main import app

    monkeypatch.setattr(config, "entorno", "produccion")
    monkeypatch.setattr(cache, "cliente", lambda: None)
    monkeypatch.setattr("app.main.cliente_redis", lambda: None)
    with pytest.raises(RuntimeError, match="Redis"):
        with TestClient(app):
            pass


def test_el_429_dice_cuando_reintentar_y_lleva_cabeceras(cliente, token_plataforma, monkeypatch):
    monkeypatch.setattr(limites.escrituras, "maximo", 1)
    cliente.post(f"{API}/galpones", headers=cabeceras(token_plataforma), json={})
    respuesta = cliente.post(f"{API}/galpones", headers=cabeceras(token_plataforma), json={})
    assert respuesta.status_code == 429
    assert int(respuesta.headers["Retry-After"]) > 0
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
