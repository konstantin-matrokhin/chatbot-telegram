"""create user table

Revision ID: 737b5e45ab82
Revises: 
Create Date: 2024-11-30 16:03:05.542685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '737b5e45ab82'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        create table "user" (
            chat_id integer not null primary key,
            username text,
            created_at timestamp,
            last_active timestamp
        );
    """)


def downgrade() -> None:
    op.execute("""
        drop table "user";
    """)
