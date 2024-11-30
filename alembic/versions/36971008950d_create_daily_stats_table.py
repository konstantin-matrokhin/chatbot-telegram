"""create daily_stats table

Revision ID: 36971008950d
Revises: 737b5e45ab82
Create Date: 2024-11-30 16:10:48.467969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36971008950d'
down_revision: Union[str, None] = '737b5e45ab82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        create table daily_stats (
            user_id integer references "user",
            messages integer not null,
            images integer not null,
            for_day date not null,
            primary key (user_id, for_day)
        );
    """)


def downgrade() -> None:
    op.execute("""
        drop table daily_stats;
    """)
