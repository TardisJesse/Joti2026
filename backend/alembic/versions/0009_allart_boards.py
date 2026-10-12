"""Populate the three requested rounds with the reviewed Allart JOTI boards."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.models import BoardInstallation
from app.board_setup import install_boards, restore_boards

revision = '0009_allart_boards'
down_revision = '0008_news_and_scanner'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # Current ORM includes the later boundary field; support upgrading from 0008.
    if 'play_area_json' not in {c['name'] for c in sa.inspect(bind).get_columns('games')}:
        op.add_column('games', sa.Column('play_area_json', sa.Text(), nullable=True))
    BoardInstallation.__table__.create(bind, checkfirst=True)
    with Session(bind=bind, join_transaction_mode='create_savepoint') as db:
        for result in install_boards(db): print('JOTI board installed:', result)
        db.commit()


def downgrade():
    with Session(bind=op.get_bind(), join_transaction_mode='create_savepoint') as db:
        restore_boards(db, 'allart-joti-2026-v1'); db.commit()
    op.drop_table('board_installations')
