"""Persist the administrator's default round for the player entry screen."""
from alembic import op
import sqlalchemy as sa
from app.models import GameSettings

revision = '0019_default_game'
down_revision = '0018_scheduled_round_start'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    GameSettings.__table__.create(bind, checkfirst=True)
    if bind.execute(sa.select(GameSettings.id).where(GameSettings.id == 1)).first() is None:
        game_id = bind.execute(sa.text(
            "SELECT id FROM games WHERE game_code IS NOT NULL "
            "ORDER BY CASE WHEN LOWER(game_code) = 'ronde-a' THEN 0 ELSE 1 END, created_at, id LIMIT 1"
        )).scalar()
        bind.execute(GameSettings.__table__.insert().values(id=1, default_game_id=game_id))


def downgrade():
    op.drop_table('game_settings')
