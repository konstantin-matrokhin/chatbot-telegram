"""create subscription table

Revision ID: 6d2d3102f190
Revises: 56951c932eb4
Create Date: 2024-11-30 16:14:17.172607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d2d3102f190'
down_revision: Union[str, None] = '56951c932eb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        create table subscription (
            id integer primary key,
            plan_name text not null,
            transaction_id integer not null references "transaction",
            start_date timestamp not null,
            end_date timestamp not null,
            created_at timestamp not null
        );
    """)


def downgrade() -> None:
    op.execute("""
        drop table subscription;
    """)
