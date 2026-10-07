"""game codes and unique team names per round

Revision ID: 0002_game_codes_and_team_names
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_game_codes_and_team_names"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if 'game_code' not in {c['name'] for c in inspector.get_columns('games')}:
        op.add_column("games", sa.Column("game_code", sa.String(length=32), nullable=True))
    if 'ix_games_game_code' not in {i['name'] for i in inspector.get_indexes('games')}:
        op.create_index("ix_games_game_code", "games", ["game_code"], unique=True)
    if 'uq_team_game_name' not in {c['name'] for c in inspector.get_unique_constraints('teams')}:
        with op.batch_alter_table('teams') as batch:
            batch.create_unique_constraint("uq_team_game_name", ["game_id", "name"])


def downgrade():
    op.drop_constraint("uq_team_game_name", "teams", type_="unique")
    op.drop_index("ix_games_game_code", table_name="games")
    op.drop_column("games", "game_code")
