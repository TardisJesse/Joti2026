"""Persistent round news and scanner locations."""
from alembic import op
from app.models import NewsEvent

revision = '0008_news_and_scanner'
down_revision = '0007_bonus_clock'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE objecttype ADD VALUE IF NOT EXISTS 'SCANNER_POINT'")
    NewsEvent.__table__.create(bind, checkfirst=True)


def downgrade():
    op.drop_table('news_events')
