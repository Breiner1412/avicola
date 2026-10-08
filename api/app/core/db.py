"""Conexion a la base de datos."""

from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import config

motor = create_engine(
    config.url_base_datos,
    # READ COMMITTED: despues de esperar un bloqueo, las consultas ven lo que otros
    # ya confirmaron (con REPEATABLE READ, el cierre de caja sumaba sobre una foto
    # vieja y no veia las ventas que entraron mientras esperaba)
    isolation_level="READ COMMITTED",
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SesionLocal = sessionmaker(bind=motor, autoflush=False, autocommit=False, future=True)


def obtener_db() -> Generator[Session, None, None]:
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()


def bloquear(db: Session, modelo, registro_id: int | None):
    """Lee la fila con SELECT ... FOR UPDATE y la deja bloqueada hasta el commit.

    Refresca el objeto con lo ultimo confirmado en la base, asi dos peticiones a la
    vez (dos clics) no trabajan sobre el mismo estado viejo: la segunda espera y ve
    lo que dejo la primera.
    """
    if registro_id is None:
        return None
    return db.execute(
        select(modelo)
        .where(modelo.id == registro_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
