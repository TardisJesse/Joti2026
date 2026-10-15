"""Set the field rewards for the requested hour-long game."""
import re
from alembic import op
from sqlalchemy.orm import Session
from app.models import CapturePoint, Duck, PhotoPoint, Puzzle, GameObject, ObjectType, Game
from app.capture_income import settle_capture_income

revision = '0014_reward_balance'
down_revision = '0013_puzzle_eight'
branch_labels = None
depends_on = None


def apply_updates(db):
    for game in db.query(Game):
        settle_capture_income(db, game.id)
    for model, points in ((Duck, 50), (PhotoPoint, 20), (Puzzle, 20)):
        db.query(model).update({'reward_points': points})
    db.query(CapturePoint).update({'capture_reward': 5, 'points_per_minute': 5})
    for obj in db.query(GameObject).filter_by(type=ObjectType.CAPTURE_POINT):
        if obj.description:
            obj.description = re.sub(r'je ontvangt \d+ volgers bij verovering', 'je ontvangt 5 volgers bij verovering', obj.description)
    db.flush()
    print('Rewards updated: ducks=50, photos=20, puzzles=20, capture=5, income=5/min')


def upgrade():
    with Session(bind=op.get_bind(), join_transaction_mode='create_savepoint') as db:
        apply_updates(db)
        db.commit()


def downgrade():
    # Keep earned scores and the requested rewards when rolling back application code.
    pass
