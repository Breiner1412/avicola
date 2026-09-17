"""Conexion a la base de datos."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import config

motor = create_engine(
    config.url_base_datos,
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
