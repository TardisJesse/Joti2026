"""Assign distinct colors to existing teams, unique within each round."""
from alembic import op
import sqlalchemy as sa
from app.team_colors import next_team_color

revision = '0003_team_colors'
down_revision = '0002_game_codes_and_team_names'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    used = {}
    for row in connection.execute(sa.text('SELECT id, game_id FROM teams ORDER BY game_id, created_at, id')).mappings():
        colors = used.setdefault(row['game_id'], set())
        color = next_team_color(colors)
        colors.add(color)
        connection.execute(sa.text('UPDATE teams SET color = :color WHERE id = :id'), {'color': color, 'id': row['id']})
    if 'uq_team_game_color' not in {c['name'] for c in sa.inspect(connection).get_unique_constraints('teams')}:
        with op.batch_alter_table('teams') as batch:
            batch.create_unique_constraint('uq_team_game_color', ['game_id', 'color'])


def downgrade():
    op.drop_constraint('uq_team_game_color', 'teams', type_='unique')
