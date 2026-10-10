"""permisos por cuenta

Cada empresa guarda sus propios permisos; los que ya existian quedan como los
de fabrica (cuenta_id vacio), que solo cambia la plataforma.

Revision ID: b3f1c2d4e5a6
Revises: 55b84ed65de7
Create Date: 2026-10-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3f1c2d4e5a6'
down_revision: Union[str, None] = '55b84ed65de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('permisos_nuevos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=True),
    sa.Column('alcance', sa.Integer(), sa.Computed('coalesce(`cuenta_id`, 0)', persisted=True), nullable=True),
    sa.Column('rol_id', sa.Integer(), nullable=False),
    sa.Column('modulo_id', sa.Integer(), nullable=False),
    sa.Column('ver', sa.Boolean(), nullable=False),
    sa.Column('crear', sa.Boolean(), nullable=False),
    sa.Column('editar', sa.Boolean(), nullable=False),
    sa.Column('borrar', sa.Boolean(), nullable=False),
    # Sin CASCADE: MySQL no lo permite en la base de una columna generada
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuentas.id']),
    sa.ForeignKeyConstraint(['modulo_id'], ['modulos.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('alcance', 'rol_id', 'modulo_id', name='uq_permiso_alcance')
    )
    op.execute(
        "INSERT INTO permisos_nuevos (cuenta_id, rol_id, modulo_id, ver, crear, editar, borrar) "
        "SELECT NULL, rol_id, modulo_id, ver, crear, editar, borrar FROM permisos"
    )
    op.drop_table('permisos')
    op.rename_table('permisos_nuevos', 'permisos')
    op.create_index(op.f('ix_permisos_cuenta_id'), 'permisos', ['cuenta_id'], unique=False)
    op.create_index(op.f('ix_permisos_rol_id'), 'permisos', ['rol_id'], unique=False)
    op.create_index(op.f('ix_permisos_modulo_id'), 'permisos', ['modulo_id'], unique=False)


def downgrade() -> None:
    # Se pierden los permisos propios de cada empresa; quedan los de fabrica
    op.create_table('permisos_viejos',
    sa.Column('rol_id', sa.Integer(), nullable=False),
    sa.Column('modulo_id', sa.Integer(), nullable=False),
    sa.Column('ver', sa.Boolean(), nullable=False),
    sa.Column('crear', sa.Boolean(), nullable=False),
    sa.Column('editar', sa.Boolean(), nullable=False),
    sa.Column('borrar', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['modulo_id'], ['modulos.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('rol_id', 'modulo_id')
    )
    op.execute(
        "INSERT INTO permisos_viejos (rol_id, modulo_id, ver, crear, editar, borrar) "
        "SELECT rol_id, modulo_id, ver, crear, editar, borrar FROM permisos WHERE cuenta_id IS NULL"
    )
    op.drop_table('permisos')
    op.rename_table('permisos_viejos', 'permisos')
