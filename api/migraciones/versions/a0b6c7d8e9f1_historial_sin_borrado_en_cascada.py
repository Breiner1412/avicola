"""historial sin borrado en cascada

Las tablas con historial (ventas, cajas, movimientos, produccion, sanidad) ya no
se borran en cascada al borrar la cuenta, la finca o el lote, ni pierden la
finca con SET NULL: la base rechaza esos borrados (RESTRICT). Las cuentas y las
fincas se desactivan, no se borran.

Revision ID: a0b6c7d8e9f1
Revises: f9a5b6c7d8e0
Create Date: 2026-10-08 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a0b6c7d8e9f1'
down_revision: Union[str, None] = 'f9a5b6c7d8e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tabla, columna, tabla referida, regla anterior)
CLAVES = [
    ('turnos_caja', 'cuenta_id', 'cuentas', 'CASCADE'),
    ('ventas', 'cuenta_id', 'cuentas', 'CASCADE'),
    ('ventas', 'finca_id', 'fincas', 'SET NULL'),
    ('movimientos_inventario', 'cuenta_id', 'cuentas', 'CASCADE'),
    ('movimientos_inventario', 'finca_id', 'fincas', 'SET NULL'),
    ('movimientos_aves', 'lote_id', 'lotes', 'CASCADE'),
    ('produccion_huevos', 'cuenta_id', 'cuentas', 'CASCADE'),
    ('produccion_huevos', 'finca_id', 'fincas', 'CASCADE'),
    ('produccion_huevos', 'lote_id', 'lotes', 'CASCADE'),
    ('aplicaciones_sanitarias', 'cuenta_id', 'cuentas', 'CASCADE'),
    ('aplicaciones_sanitarias', 'finca_id', 'fincas', 'CASCADE'),
    ('aplicaciones_sanitarias', 'lote_id', 'lotes', 'CASCADE'),
]


def _cambiar(regla_nueva: str | None) -> None:
    inspector = sa.inspect(op.get_bind())
    for tabla, columna, referida, anterior in CLAVES:
        actual = next(
            c for c in inspector.get_foreign_keys(tabla)
            if c['constrained_columns'] == [columna] and c['referred_table'] == referida
        )
        op.drop_constraint(actual['name'], tabla, type_='foreignkey')
        op.create_foreign_key(
            actual['name'], tabla, referida, [columna], ['id'], ondelete=regla_nueva or anterior
        )


def upgrade() -> None:
    _cambiar('RESTRICT')


def downgrade() -> None:
    _cambiar(None)
