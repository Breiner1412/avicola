"""El registro de cambios es de solo insercion, tambien dentro de la base."""

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError

from app.core.db import SesionLocal
from app.modelos.registro import Auditoria


@pytest.fixture()
def linea(cliente, token_plataforma):
    # El inicio de sesion de token_plataforma ya dejo lineas en el registro
    with SesionLocal() as db:
        ultima = db.scalar(select(func.max(Auditoria.id)))
    assert ultima is not None
    return ultima


def test_no_se_puede_editar(linea):
    with SesionLocal() as db, pytest.raises(DBAPIError, match="solo insercion"):
        db.execute(update(Auditoria).where(Auditoria.id == linea).values(descripcion="alterado"))
        db.commit()


def test_no_se_puede_borrar(linea):
    with SesionLocal() as db, pytest.raises(DBAPIError, match="solo insercion"):
        db.execute(delete(Auditoria).where(Auditoria.id == linea))
        db.commit()
    with SesionLocal() as db:
        assert db.get(Auditoria, linea) is not None

