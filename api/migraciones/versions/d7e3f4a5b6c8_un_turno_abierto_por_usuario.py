"""un turno abierto por usuario

Columna generada abierto_de (el usuario, solo mientras el turno esta abierto)
con indice unico: dos peticiones a la vez no dejan dos cajas abiertas.

Revision ID: d7e3f4a5b6c8
Revises: c5d2e3f4a6b7
Create Date: 2026-10-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7e3f4a5b6c8'
down_revision: Union[str, None] = 'c5d2e3f4a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Si ya hubiera usuarios con dos turnos abiertos, se deja abierto solo el ultimo
    op.execute(
        "UPDATE turnos_caja t JOIN ("
        "  SELECT usuario_id, MAX(id) AS ultimo FROM turnos_caja WHERE estado = 'abierto' GROUP BY usuario_id"
        ") u ON u.usuario_id = t.usuario_id "
        "SET t.estado = 'cerrado', t.cerrado_en = NOW(), "
        "    t.observaciones = 'Cerrado al migrar: habia otra caja abierta' "
        "WHERE t.estado = 'abierto' AND t.id <> u.ultimo"
    )
    op.add_column(
        'turnos_caja',
        sa.Column(
            'abierto_de',
            sa.Integer(),
            sa.Computed("(case when `estado` = 'abierto' then `usuario_id` end)", persisted=True),
            nullable=True,
        ),
    )
    op.create_unique_constraint('uq_turno_abierto_por_usuario', 'turnos_caja', ['abierto_de'])


def downgrade() -> None:
    op.drop_constraint('uq_turno_abierto_por_usuario', 'turnos_caja', type_='unique')
    op.drop_column('turnos_caja', 'abierto_de')
