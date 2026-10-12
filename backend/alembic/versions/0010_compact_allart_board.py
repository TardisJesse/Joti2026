"""Install the approved compact field with central masts and Holywood scanner."""
import json
from pathlib import Path
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.board_setup import install_boards, restore_boards, normalized
from app.models import Game, BoardInstallation

revision = '0010_compact_allart_board'
down_revision = '0009_allart_boards'
branch_labels = None
depends_on = None
VERSION = 'allart-joti-2026-compact-v2'

def upgrade():
    bind = op.get_bind()
    if 'play_area_json' not in {c['name'] for c in sa.inspect(bind).get_columns('games')}:
        op.add_column('games', sa.Column('play_area_json', sa.Text(), nullable=True))
    pack = json.loads((Path(__file__).parents[2] / 'app/data/allart_joti_2026_compact_v2.json').read_text(encoding='utf-8'))
    with Session(bind=bind, join_transaction_mode='create_savepoint') as db:
        for row in install_boards(db, pack): print('Compact JOTI board installed:', row)
        for game in db.query(Game):
            if normalized(game.game_code) == 'rondetest' or normalized(game.name) == 'rondetest':
                game.play_area_json = json.dumps(pack['play_area'])
        db.commit()

def downgrade():
    with Session(bind=op.get_bind(), join_transaction_mode='create_savepoint') as db:
        restore_boards(db, VERSION)
        db.query(BoardInstallation).filter_by(version=VERSION).delete()
        for game in db.query(Game):
            if normalized(game.game_code) == 'rondetest' or normalized(game.name) == 'rondetest':
                game.play_area_json = None
        db.commit()
    # Keep the nullable column for compatibility with the current ORM on rollback.
