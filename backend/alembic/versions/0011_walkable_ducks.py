"""Add numbered NFC identities; default locations are loaded explicitly by admins."""
from alembic import op
import sqlalchemy as sa

revision = '0011_walkable_ducks'
down_revision = '0010_compact_allart_board'
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c['name'] for c in inspector.get_columns('ducks')}
    if 'duck_number' not in columns:
        op.add_column('ducks', sa.Column('duck_number', sa.Integer(), nullable=True))
    if 'nfc_serial_hash' not in columns:
        op.add_column('ducks', sa.Column('nfc_serial_hash', sa.String(64), nullable=True))
    if 'ix_ducks_nfc_serial_hash' not in {i['name'] for i in inspector.get_indexes('ducks')}:
        op.create_index('ix_ducks_nfc_serial_hash', 'ducks', ['nfc_serial_hash'])

def downgrade():
    # Retain nullable columns so current ORM and recorded game history remain usable.
    pass
