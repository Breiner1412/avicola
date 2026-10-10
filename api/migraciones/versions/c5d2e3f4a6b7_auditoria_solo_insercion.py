"""auditoria solo insercion

El registro de cambios no se puede editar ni borrar: dos triggers rechazan
UPDATE y DELETE sobre la tabla. Se quitan sus claves foraneas, porque un
ON DELETE SET NULL reescribia filas y las cascadas de InnoDB no pasan por
los triggers.

Crear triggers con el binlog activo exige que MySQL arranque con
--log-bin-trust-function-creators=1 (ver docker-compose).

Revision ID: c5d2e3f4a6b7
Revises: b3f1c2d4e5a6
Create Date: 2026-10-08 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5d2e3f4a6b7'
down_revision: Union[str, None] = 'b3f1c2d4e5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MENSAJE = "El registro de cambios es de solo insercion"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for clave in inspector.get_foreign_keys('auditoria'):
        op.drop_constraint(clave['name'], 'auditoria', type_='foreignkey')

    # Los indices que MySQL creo para esas claves quedan con nombres propios
    for indice in sa.inspect(op.get_bind()).get_indexes('auditoria'):
        if indice['column_names'] in (['finca_id'], ['usuario_id'], ['cuenta_id']):
            op.drop_index(indice['name'], table_name='auditoria')
    op.create_index(op.f('ix_auditoria_finca_id'), 'auditoria', ['finca_id'], unique=False)
    op.create_index(op.f('ix_auditoria_usuario_id'), 'auditoria', ['usuario_id'], unique=False)

    op.execute(
        "CREATE TRIGGER auditoria_sin_cambios BEFORE UPDATE ON auditoria FOR EACH ROW "
        f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{MENSAJE}'"
    )
    op.execute(
        "CREATE TRIGGER auditoria_sin_borrar BEFORE DELETE ON auditoria FOR EACH ROW "
        f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{MENSAJE}'"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS auditoria_sin_borrar")
    op.execute("DROP TRIGGER IF EXISTS auditoria_sin_cambios")
    op.drop_index(op.f('ix_auditoria_usuario_id'), table_name='auditoria')
    op.drop_index(op.f('ix_auditoria_finca_id'), table_name='auditoria')
    op.create_foreign_key(None, 'auditoria', 'cuentas', ['cuenta_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(None, 'auditoria', 'fincas', ['finca_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(None, 'auditoria', 'usuarios', ['usuario_id'], ['id'], ondelete='SET NULL')
