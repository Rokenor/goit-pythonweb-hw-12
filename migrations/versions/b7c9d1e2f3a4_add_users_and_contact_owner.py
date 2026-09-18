"""Таблиця users і прив'язка контактів до власника

Revision ID: b7c9d1e2f3a4
Revises: e1f2a3b4c5d6
Create Date: 2026-09-14 12:00:00.000000

Контакти, створені до появи аутентифікації, не мають власника і призначити
його неможливо, тому їх видаляємо, перш ніж `contacts.user_id` стане NOT NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c9d1e2f3a4"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("avatar", sa.String(length=255), nullable=True),
        sa.Column(
            "confirmed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # тепер email унікальний у межах власника, а не глобально
    op.drop_index(op.f("ix_contacts_email"), table_name="contacts")

    op.add_column("contacts", sa.Column("user_id", sa.Integer(), nullable=True))
    op.execute("DELETE FROM contacts WHERE user_id IS NULL")
    op.alter_column("contacts", "user_id", nullable=False)

    op.create_foreign_key(
        "fk_contacts_user_id_users",
        "contacts",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_contacts_user_id"), "contacts", ["user_id"])
    op.create_index(op.f("ix_contacts_email"), "contacts", ["email"])
    op.create_unique_constraint(
        "uq_contacts_email_user", "contacts", ["email", "user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_contacts_email_user", "contacts", type_="unique")
    op.drop_index(op.f("ix_contacts_email"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_user_id"), table_name="contacts")
    op.drop_constraint("fk_contacts_user_id_users", "contacts", type_="foreignkey")
    op.drop_column("contacts", "user_id")
    op.create_index(op.f("ix_contacts_email"), "contacts", ["email"], unique=True)

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
