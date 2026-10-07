"""Persist browser push subscriptions."""
from alembic import op
import sqlalchemy as sa
revision = '0004_web_push'
down_revision = '0003_team_colors'
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table('push_subscriptions'):
        return
    op.create_table('push_subscriptions', sa.Column('id', sa.String(36), primary_key=True), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False), sa.Column('endpoint', sa.Text, nullable=False, unique=True), sa.Column('keys_json', sa.Text, nullable=False))
    op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'])


def downgrade():
    op.drop_table('push_subscriptions')
