"""Persist an optional pre-game countdown without changing existing rounds."""
from alembic import op
import sqlalchemy as sa

revision = '0018_scheduled_round_start'
down_revision = '0017_reset_rounds_remove_teams'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('games')}
    if 'scheduled_start_at' not in columns:
        op.add_column('games', sa.Column('scheduled_start_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('games', 'scheduled_start_at')
