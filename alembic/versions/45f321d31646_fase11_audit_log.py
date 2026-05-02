"""fase11 - audit log

Revision ID: 45f321d31646
Revises: fase2_a1b2c3d4e5f6
Create Date: 2026-05-02 07:19:52.739932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45f321d31646'
down_revision: Union[str, Sequence[str], None] = 'fase2_a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id',         sa.UUID(),              nullable=False),
        sa.Column('admin_id',   sa.UUID(),              nullable=False),
        sa.Column('aksi',       sa.String(length=100),  nullable=False),
        sa.Column('entitas',    sa.String(length=50),   nullable=True),
        sa.Column('entitas_id', sa.String(length=100),  nullable=True),
        sa.Column('detail',     sa.Text(),              nullable=True),
        sa.Column('ip_address', sa.String(length=45),   nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True
        ),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_audit_log_admin_id',   'audit_log', ['admin_id'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    op.create_index('ix_audit_log_entitas',    'audit_log', ['entitas'])


def downgrade() -> None:
    op.drop_index('ix_audit_log_entitas',    table_name='audit_log')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_admin_id',   table_name='audit_log')
    op.drop_table('audit_log')
