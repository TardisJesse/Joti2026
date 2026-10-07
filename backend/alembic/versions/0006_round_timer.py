"""Persist remaining timer time while a round is paused."""
from alembic import op
import sqlalchemy as sa

revision = '0006_round_timer'
down_revision = '0005_photos_and_income'
branch_labels = None
depends_on = None


def upgrade():
    if 'timer_remaining_seconds' not in {column['name'] for column in sa.inspect(op.get_bind()).get_columns('games')}:
        op.add_column('games', sa.Column('timer_remaining_seconds', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('games', 'timer_remaining_seconds')
