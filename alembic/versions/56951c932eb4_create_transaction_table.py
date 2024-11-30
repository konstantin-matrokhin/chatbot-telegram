"""create transaction table

Revision ID: 56951c932eb4
Revises: 36971008950d
Create Date: 2024-11-30 16:14:06.922567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56951c932eb4'
down_revision: Union[str, None] = '36971008950d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        create table "transaction" (
            id integer primary key,
            user_id integer references "user",
            amount integer not null,
            currency text not null,
            status text not null,
            created_at timestamp not null
        );
    """)


def downgrade() -> None:
    op.execute("""
        drop table "transaction";
    """)
