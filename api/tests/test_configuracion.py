"""En produccion la API no arranca con configuracion de ejemplo."""

import pytest
from pydantic import ValidationError

from app.core.config import Configuracion

SEGURA = {
    "entorno": "produccion",
    "jwt_secret": "x" * 48,
    "admin_password": "UnaClaveLargaDeVerdad2026",
    "db_password": "OtraClaveDeLaBase2026",
    "cookie_segura": True,
}


def test_una_configuracion_segura_arranca():
    assert Configuracion(_env_file=None, **SEGURA).es_produccion


@pytest.mark.parametrize(
    "cambio",
    [
        {"jwt_secret": "cambia-esta-clave-por-una-larga-y-aleatoria-de-32-o-mas"},
        {"admin_password": "Admin12345"},
        {"admin_password": "corta"},
        {"db_password": "CambiaEstaClave123"},
        {"cookie_segura": False},
    ],
)
def test_en_produccion_se_rechazan_los_valores_de_ejemplo(cambio):
    with pytest.raises(ValidationError, match="insegura"):
        Configuracion(_env_file=None, **{**SEGURA, **cambio})


def test_en_desarrollo_se_permiten():
    Configuracion(_env_file=None, **{**SEGURA, "entorno": "desarrollo", "admin_password": "Admin12345", "cookie_segura": False})
