"""message edited_at and is_deleted

Revision ID: c7d41e9a05b2
Revises: b3fdce757824
Create Date: 2026-10-10 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d41e9a05b2'
down_revision: Union[str, Sequence[str], None] = 'b3fdce757824'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default na false sa is_deleted: tatanggapin ng mga dati nang row
    op.add_column('messages', sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('messages', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('group_messages', sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('group_messages', sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('group_messages', 'is_deleted')
    op.drop_column('group_messages', 'edited_at')
    op.drop_column('messages', 'is_deleted')
    op.drop_column('messages', 'edited_at')
