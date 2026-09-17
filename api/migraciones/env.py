"""Configuracion de Alembic: toma la conexion del archivo .env del proyecto."""

from logging.config import fileConfig

from alembic import context

from app.core.config import config as ajustes
from app.core.db import motor
from app.modelos import Base  # importa todos los modelos

configuracion = context.config
if configuracion.config_file_name is not None:
    fileConfig(configuracion.config_file_name)

metadatos = Base.metadata


def offline() -> None:
    context.configure(
        url=ajustes.url_base_datos.render_as_string(hide_password=False),
        target_metadata=metadatos,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def online() -> None:
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=metadatos, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    offline()
else:
    online()
