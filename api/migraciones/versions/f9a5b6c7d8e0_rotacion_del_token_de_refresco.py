"""rotacion del token de refresco

Revision ID: f9a5b6c7d8e0
Revises: e8f4a5b6c7d9
Create Date: 2026-10-08 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f9a5b6c7d8e0'
down_revision: Union[str, None] = 'e8f4a5b6c7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sesiones', sa.Column('huella_anterior', sa.String(length=64), nullable=True))
    op.add_column('sesiones', sa.Column('rotada_en', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_sesiones_huella_anterior'), 'sesiones', ['huella_anterior'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sesiones_huella_anterior'), table_name='sesiones')
    op.drop_column('sesiones', 'rotada_en')
    op.drop_column('sesiones', 'huella_anterior')
