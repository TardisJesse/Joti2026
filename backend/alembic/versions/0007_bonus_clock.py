"""Keep rotating bonus time across pauses and server restarts."""
from alembic import op
import sqlalchemy as sa

revision = '0007_bonus_clock'
down_revision = '0006_round_timer'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('games')}
    if 'bonus_elapsed_seconds' not in columns:
        op.add_column('games', sa.Column('bonus_elapsed_seconds', sa.Float(), nullable=False, server_default='0'))
    if 'bonus_updated_at' not in columns:
        op.add_column('games', sa.Column('bonus_updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('games', 'bonus_updated_at')
    op.drop_column('games', 'bonus_elapsed_seconds')
