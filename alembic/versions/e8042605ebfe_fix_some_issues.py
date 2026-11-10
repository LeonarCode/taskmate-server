"""fix some issues

Revision ID: e8042605ebfe
Revises: 10fcef6b1b08
Create Date: 2026-10-05 06:32:06.382911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8042605ebfe'
down_revision: Union[str, Sequence[str], None] = '10fcef6b1b08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # rename lang (hindi drop/create): hindi mawawala ang data, at kusang susunod
    # ang notifications_reference_id_fkey sa bagong pangalan ng table
    op.rename_table('references', 'notif_references')
    op.add_column('group_tasks', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('group_tasks', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('group_tasks', sa.Column('client_id', sa.String(length=36), nullable=True))
    op.alter_column('group_tasks', 'server_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.create_unique_constraint('group_tasks_client_id_key', 'group_tasks', ['client_id'])
    op.drop_constraint('messages_task_ref_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_task_ref_id_fkey', 'messages', 'tasks', ['task_ref_id'], ['id'], ondelete='SET NULL')
    op.alter_column('ratings', 'score',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               type_=sa.Numeric(precision=3, scale=2, asdecimal=False),
               existing_nullable=False)
    op.create_unique_constraint('uq_rating_once_per_server', 'ratings', ['rater_id', 'rated_id', 'server_id'])
    # hindi nakikita ng autogenerate ang CheckConstraint, kaya mano-mano ito
    op.create_check_constraint('ck_rating_score_range', 'ratings', 'score >= 0 AND score <= 5')
    op.create_check_constraint('ck_rating_not_self', 'ratings', 'rater_id <> rated_id')
    op.create_unique_constraint('uq_member_server_user', 'server_members', ['server_id', 'user_id'])
    op.alter_column('servers', 'icon_emoji',
               existing_type=sa.VARCHAR(length=1),
               type_=sa.String(length=16),
               existing_nullable=True)
    op.add_column('tasks', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('tasks', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('tasks', sa.Column('client_id', sa.String(length=36), nullable=True))
    op.create_unique_constraint('tasks_client_id_key', 'tasks', ['client_id'])
    op.alter_column('users', 'average_rating',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               type_=sa.Numeric(precision=3, scale=2, asdecimal=False),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'average_rating',
               existing_type=sa.Numeric(precision=3, scale=2, asdecimal=False),
               type_=sa.NUMERIC(precision=10, scale=2),
               existing_nullable=False)
    op.drop_constraint('tasks_client_id_key', 'tasks', type_='unique')
    op.drop_column('tasks', 'client_id')
    op.drop_column('tasks', 'updated_at')
    op.drop_column('tasks', 'created_at')
    op.alter_column('servers', 'icon_emoji',
               existing_type=sa.String(length=16),
               type_=sa.VARCHAR(length=1),
               existing_nullable=True)
    op.drop_constraint('uq_member_server_user', 'server_members', type_='unique')
    op.drop_constraint('ck_rating_not_self', 'ratings', type_='check')
    op.drop_constraint('ck_rating_score_range', 'ratings', type_='check')
    op.drop_constraint('uq_rating_once_per_server', 'ratings', type_='unique')
    op.alter_column('ratings', 'score',
               existing_type=sa.Numeric(precision=3, scale=2, asdecimal=False),
               type_=sa.NUMERIC(precision=10, scale=2),
               existing_nullable=False)
    op.drop_constraint('messages_task_ref_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_task_ref_id_fkey', 'messages', 'tasks', ['task_ref_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('group_tasks_client_id_key', 'group_tasks', type_='unique')
    op.alter_column('group_tasks', 'server_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_column('group_tasks', 'client_id')
    op.drop_column('group_tasks', 'updated_at')
    op.drop_column('group_tasks', 'created_at')
    op.rename_table('notif_references', 'references')
