"""restricciones e indices

- CHECK: existencias, stock de huevos y aves de lotes y galpones nunca negativas;
  valores de una venta no negativos y pagos mayores que cero.
- Indices compuestos para los filtros mas usados (ventas por cuenta, punto y
  turno; turnos por usuario; lecturas por sensor y fecha; registro por cuenta,
  finca y fecha; avisos activos por cuenta).
- BIGINT en las tablas que mas crecen (registro, lecturas y detalles de venta).

Revision ID: b1c7d8e9f0a2
Revises: a0b6c7d8e9f1
Create Date: 2026-10-08 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = 'b1c7d8e9f0a2'
down_revision: Union[str, None] = 'a0b6c7d8e9f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (nombre, tabla, condicion)
CHEQUEOS = [
    ('ck_existencia_no_negativa', 'existencias', 'cantidad >= 0'),
    ('ck_stock_huevos_no_negativo', 'stock_huevos', 'cantidad >= 0'),
    ('ck_lote_aves_no_negativas', 'lotes', 'aves_actuales >= 0 and aves_descarte >= 0'),
    ('ck_galpon_aves_no_negativas', 'galpones', 'aves_actuales >= 0'),
    ('ck_venta_valores_no_negativos', 'ventas', 'subtotal >= 0 and descuento >= 0 and total >= 0'),
    ('ck_pago_positivo', 'venta_pagos', 'monto > 0'),
]

INDICES = [
    ('ix_alertas_cuenta_activa', 'alertas', ['cuenta_id', 'activa']),
    ('ix_auditoria_cuenta_finca_fecha', 'auditoria', ['cuenta_id', 'finca_id', 'creado_en']),
    ('ix_lecturas_sensor_fecha', 'lecturas_sensor', ['sensor_id', 'medido_en']),
    ('ix_turnos_usuario_estado', 'turnos_caja', ['usuario_id', 'estado']),
    ('ix_ventas_cuenta_fecha', 'ventas', ['cuenta_id', 'fecha']),
    ('ix_ventas_punto_fecha', 'ventas', ['punto_venta_id', 'fecha']),
    ('ix_ventas_turno_estado', 'ventas', ['turno_id', 'estado']),
]

GRANDES = ['auditoria', 'lecturas_sensor', 'venta_detalles']


def upgrade() -> None:
    # Antes de poner un CHECK se revisa que los datos lo cumplan: si no, se avisa
    # en lugar de cambiar datos sin que nadie se entere
    conexion = op.get_bind()
    malos = []
    for nombre, tabla, condicion in CHEQUEOS:
        cuantos = conexion.execute(sa.text(f"SELECT COUNT(*) FROM {tabla} WHERE NOT ({condicion})")).scalar()
        if cuantos:
            malos.append(f"{tabla}: {cuantos} filas no cumplen '{condicion}'")
    if malos:
        raise RuntimeError("Corrige estos datos antes de migrar: " + "; ".join(malos))

    for nombre, tabla, condicion in CHEQUEOS:
        op.create_check_constraint(nombre, tabla, condicion)
    for nombre, tabla, columnas in INDICES:
        op.create_index(nombre, tabla, columnas, unique=False)
    for tabla in GRANDES:
        op.alter_column(tabla, 'id', existing_type=mysql.INTEGER(), type_=sa.BigInteger(),
                        existing_nullable=False, autoincrement=True)


def downgrade() -> None:
    for tabla in GRANDES:
        op.alter_column(tabla, 'id', existing_type=sa.BigInteger(), type_=mysql.INTEGER(),
                        existing_nullable=False, autoincrement=True)
    for nombre, tabla, _columnas in INDICES:
        op.drop_index(nombre, table_name=tabla)
    for nombre, tabla, _condicion in CHEQUEOS:
        op.drop_constraint(nombre, tabla, type_='check')
