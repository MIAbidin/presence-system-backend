"""fase D - add program_studi table

Revision ID: 0e9f578bfa03
Revises: c248e6e34f29
Create Date: 2026-05-05 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0e9f578bfa03"
down_revision: Union[str, Sequence[str], None] = "c248e6e34f29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "program_studi",
        sa.Column("id",        sa.UUID(),             nullable=False),
        sa.Column("kode",      sa.String(length=10),  nullable=False),
        sa.Column("nama",      sa.String(length=100), nullable=False),
        sa.Column("fakultas",  sa.String(length=100), nullable=True),
        sa.Column("jenjang",   sa.String(length=5),   nullable=True),
        sa.Column("is_active", sa.Boolean(),          nullable=False,
                  server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kode", name="uq_program_studi_kode"),
    )
    op.create_index("ix_program_studi_kode",     "program_studi", ["kode"],      unique=True)
    op.create_index("ix_program_studi_is_active", "program_studi", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_program_studi_is_active", table_name="program_studi")
    op.drop_index("ix_program_studi_kode",      table_name="program_studi")
    op.drop_table("program_studi")