"""El historial no se puede borrar en cascada desde la base."""

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.db import SesionLocal
from app.modelos.aves import Lote
from app.modelos.organizacion import Finca
from tests.conftest import API, cabeceras
from tests.test_multicuenta import crear_cuenta_completa


def test_no_se_borra_un_lote_con_historial(cliente, token_plataforma):
    datos = crear_cuenta_completa(cliente, token_plataforma, "Historial")
    cab = cabeceras(datos["token"], datos["finca_id"])
    galpon = cliente.post(f"{API}/galpones", headers=cab, json={"codigo": "G1", "nombre": "G1", "capacidad": 900}).json()
    lote = cliente.post(
        f"{API}/lotes",
        headers=cab,
        json={"codigo": "LH", "galpon_id": galpon["id"], "fecha_ingreso": "2026-01-05", "aves_iniciales": 100},
    ).json()
    muerte = cliente.post(
        f"{API}/movimientos-aves",
        headers=cab,
        json={"lote_id": lote["id"], "fecha": "2026-01-10", "tipo": "muerte", "cantidad": 2},
    )
    assert muerte.status_code == 201, muerte.text

    with SesionLocal() as db, pytest.raises(IntegrityError):
        db.execute(delete(Lote).where(Lote.id == lote["id"]))
        db.commit()
    with SesionLocal() as db, pytest.raises(IntegrityError):
        db.execute(delete(Finca).where(Finca.id == datos["finca_id"]))
        db.commit()
    with SesionLocal() as db:
        assert db.scalar(select(Lote.id).where(Lote.id == lote["id"])) is not None


def test_la_base_no_deja_existencias_ni_aves_negativas():
    from sqlalchemy import text

    with SesionLocal() as db, pytest.raises(Exception, match="ck_galpon_aves_no_negativas|3819"):
        db.execute(text("UPDATE galpones SET aves_actuales = -1 LIMIT 1"))
        db.commit()
