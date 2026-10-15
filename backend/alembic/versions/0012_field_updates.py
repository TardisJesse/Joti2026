"""Apply the requested field settings and remove obsolete test rounds once."""
from alembic import op
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.board_setup import normalized
from app.models import (Game, GameObject, Team, User, UserRole, CapturePoint, Puzzle,
                        PhotoPoint, Duck, PuzzleAttempt, PhotoSubmission, DuckScan,
                        CaptureEvent, ScoreEvent, PushSubscription, NewsEvent, BoardInstallation)

revision = '0012_field_updates'
down_revision = '0011_walkable_ducks'
branch_labels = None
depends_on = None

WARNING = ' Blijf op de toegankelijke wandelpaden en laat ruimte voor andere wandelaars en fietsers.'


def apply_updates(db):
    for obj in db.query(GameObject):
        if obj.description:
            text = obj.description.replace(WARNING, '')
            if obj.type == 'CAPTURE_POINT':
                import re
                text = re.sub(r'Houd \d+ seconden de zone vast', 'Houd 10 seconden de zone vast', text)
            obj.description = text
    db.query(CapturePoint).update({'capture_seconds': 10})
    keep = {'rondea', 'rondeb', 'rondetest'}
    removed = [game for game in db.query(Game) if normalized(game.game_code) not in keep and normalized(game.name) not in keep]
    for game in removed:
        teams = [row.id for row in db.query(Team).filter_by(game_id=game.id)]
        users = [row.id for row in db.query(User).filter(User.team_id.in_(teams), User.role != UserRole.ADMIN)]
        objects = [row.id for row in db.query(GameObject).filter_by(game_id=game.id)]
        def ids(model):
            return [row.id for row in db.query(model).filter(model.game_object_id.in_(objects))]
        for model, foreign_key, values in (
            (PuzzleAttempt, PuzzleAttempt.puzzle_id, ids(Puzzle)),
            (PhotoSubmission, PhotoSubmission.photo_point_id, ids(PhotoPoint)),
            (DuckScan, DuckScan.duck_id, ids(Duck)),
            (CaptureEvent, CaptureEvent.capture_point_id, ids(CapturePoint)),
        ):
            db.query(model).filter(or_(foreign_key.in_(values), model.team_id.in_(teams), model.user_id.in_(users))).delete(synchronize_session=False)
        db.query(ScoreEvent).filter(ScoreEvent.team_id.in_(teams)).delete(synchronize_session=False)
        db.query(PushSubscription).filter(PushSubscription.user_id.in_(users)).delete(synchronize_session=False)
        db.query(CapturePoint).filter(CapturePoint.owner_team_id.in_(teams)).update({'owner_team_id': None, 'income_updated_at': None}, synchronize_session=False)
        db.query(User).filter(User.team_id.in_(teams), User.role == UserRole.ADMIN).update({'team_id': None}, synchronize_session=False)
        db.query(User).filter(User.id.in_(users)).delete(synchronize_session=False)
        for model in (Puzzle, PhotoPoint, Duck, CapturePoint):
            db.query(model).filter(model.game_object_id.in_(objects)).delete(synchronize_session=False)
        db.query(GameObject).filter_by(game_id=game.id).delete(synchronize_session=False)
        for model in (NewsEvent, BoardInstallation, Team):
            db.query(model).filter_by(game_id=game.id).delete(synchronize_session=False)
        db.delete(game)
    db.flush()
    print('Field updates: capture=10s; obsolete rounds removed:', len(removed))
    print('Remaining rounds:', ', '.join(game.game_code or game.name for game in db.query(Game)))


def upgrade():
    with Session(bind=op.get_bind(), join_transaction_mode='create_savepoint') as db:
        apply_updates(db)
        db.commit()


def downgrade():
    # Deleted test history cannot be recreated; retain the requested field settings.
    pass
