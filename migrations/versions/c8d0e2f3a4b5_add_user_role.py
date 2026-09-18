"""Роль користувача (user/admin)

Revision ID: c8d0e2f3a4b5
Revises: b7c9d1e2f3a4
Create Date: 2026-09-18 12:00:00.000000

Наявним користувачам призначається роль `user`: підвищення до `admin`
робиться свідомо, а не міграцією.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d0e2f3a4b5"
down_revision: Union[str, None] = "b7c9d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("USER", "ADMIN", name="user_role")


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", user_role, nullable=False, server_default="USER"),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    user_role.drop(op.get_bind(), checkfirst=True)
