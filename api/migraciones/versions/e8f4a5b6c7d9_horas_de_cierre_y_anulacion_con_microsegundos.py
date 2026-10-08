"""horas de cierre y anulacion con microsegundos

El cierre de caja y la anulacion de una venta se comparan para saber si la venta
se anulo despues de cerrar; con segundos enteros podian empatar.

Revision ID: e8f4a5b6c7d9
Revises: d7e3f4a5b6c8
Create Date: 2026-10-08 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import mysql


revision: str = 'e8f4a5b6c7d9'
down_revision: Union[str, None] = 'd7e3f4a5b6c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('turnos_caja', 'cerrado_en', existing_type=mysql.DATETIME(), type_=mysql.DATETIME(fsp=6), existing_nullable=True)
    op.alter_column('ventas', 'anulada_en', existing_type=mysql.DATETIME(), type_=mysql.DATETIME(fsp=6), existing_nullable=True)


def downgrade() -> None:
    op.alter_column('ventas', 'anulada_en', existing_type=mysql.DATETIME(fsp=6), type_=mysql.DATETIME(), existing_nullable=True)
    op.alter_column('turnos_caja', 'cerrado_en', existing_type=mysql.DATETIME(fsp=6), type_=mysql.DATETIME(), existing_nullable=True)
