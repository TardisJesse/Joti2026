"""Allow one-time scanner score events without rewriting existing scores."""
from alembic import op

revision = '0015_scanner_rewards'
down_revision = '0014_reward_balance'
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE scoretype ADD VALUE IF NOT EXISTS 'SCANNER_USED'")


def downgrade():
    # PostgreSQL cannot remove an enum value without replacing the type.
    # Keep existing scanner rewards and all other scoring history intact.
    pass
