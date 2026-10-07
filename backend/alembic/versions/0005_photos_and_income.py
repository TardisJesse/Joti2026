"""Profile photos, photo challenges and persistent capture income."""
from alembic import op
import sqlalchemy as sa
from app.models import PhotoPoint, PhotoSubmission

revision = '0005_photos_and_income'
down_revision = '0004_web_push'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE objecttype ADD VALUE IF NOT EXISTS 'PHOTO_POINT'")
            op.execute("ALTER TYPE scoretype ADD VALUE IF NOT EXISTS 'CAPTURE_INCOME'")
            op.execute("ALTER TYPE scoretype ADD VALUE IF NOT EXISTS 'PHOTO_SUBMITTED'")
    # 0001 uses current metadata on fresh installs; also support existing schemas.
    user_columns = {c['name'] for c in sa.inspect(bind).get_columns('users')}
    if 'profile_image' not in user_columns:
        op.add_column('users', sa.Column('profile_image', sa.Text(), nullable=True))
    columns = {c['name'] for c in sa.inspect(bind).get_columns('capture_points')}
    for column in [sa.Column('points_per_minute', sa.Integer(), nullable=False, server_default='1'), sa.Column('income_updated_at', sa.DateTime(timezone=True), nullable=True), sa.Column('income_remainder_seconds', sa.Float(), nullable=False, server_default='0')]:
        if column.name not in columns:
            op.add_column('capture_points', column)
    op.execute('UPDATE capture_points SET income_updated_at = CURRENT_TIMESTAMP WHERE owner_team_id IS NOT NULL AND income_updated_at IS NULL')
    PhotoPoint.__table__.create(bind, checkfirst=True)
    PhotoSubmission.__table__.create(bind, checkfirst=True)


def downgrade():
    op.drop_table('photo_submissions')
    op.drop_table('photo_points')
    op.drop_column('users', 'profile_image')
    for name in ('income_remainder_seconds', 'income_updated_at', 'points_per_minute'):
        op.drop_column('capture_points', name)
    # PostgreSQL enum additions remain until the type itself is removed.
