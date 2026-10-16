"""Perform the requested one-time full round and team reset."""
from alembic import op
from sqlalchemy.orm import Session

from app.models import (
    CaptureEvent, CapturePoint, DuckScan, Game, GameStatus, NewsEvent,
    PhotoSubmission, PushSubscription, PuzzleAttempt, ScoreEvent, Team, User, UserRole,
)

revision = '0017_reset_rounds_remove_teams'
down_revision = '0016_duck_names_score_reset'
branch_labels = None
depends_on = None


def upgrade():
    with Session(bind=op.get_bind(), join_transaction_mode='create_savepoint') as db:
        # Serialize with joining teams, game actions and round-clock updates.
        rounds = db.query(Game).order_by(Game.id).with_for_update().all()
        db.query(Team).order_by(Team.id).with_for_update().all()
        admins_before = db.query(User).filter_by(role=UserRole.ADMIN).count()
        counts = {}
        for model in (ScoreEvent, PhotoSubmission, DuckScan, PuzzleAttempt, CaptureEvent, NewsEvent):
            counts[model.__tablename__] = db.query(model).delete(synchronize_session=False)

        # Release team references before removing player accounts and teams.
        db.query(CapturePoint).update({
            'owner_team_id': None, 'income_updated_at': None,
            'income_remainder_seconds': 0,
        }, synchronize_session=False)
        player_ids = db.query(User.id).filter(User.role != UserRole.ADMIN)
        db.query(PushSubscription).filter(PushSubscription.user_id.in_(player_ids)).delete(
            synchronize_session=False,
        )
        db.query(User).filter_by(role=UserRole.ADMIN).update(
            {'team_id': None}, synchronize_session=False,
        )
        counts['players'] = db.query(User).filter(User.role != UserRole.ADMIN).delete(
            synchronize_session=False,
        )
        counts['teams'] = db.query(Team).delete(synchronize_session=False)

        for game in rounds:
            game.status = GameStatus.READY
            game.starts_at = None
            game.ends_at = None
            game.timer_remaining_seconds = None
            game.bonus_elapsed_seconds = 0
            game.bonus_updated_at = None
        db.flush()

        # Abort the transaction if anything was retained accidentally or an admin
        # was removed. The board objects, configuration and admin logins stay.
        remaining = sum(db.query(model).count() for model in (
            Team, ScoreEvent, PhotoSubmission, DuckScan, PuzzleAttempt, CaptureEvent,
        ))
        if remaining or db.query(User).filter(User.role != UserRole.ADMIN).count():
            raise RuntimeError('Full round reset left team data behind')
        if db.query(User).filter_by(role=UserRole.ADMIN).count() != admins_before:
            raise RuntimeError('Full round reset changed the admin accounts')
        db.commit()
        print(f'Full reset complete: rounds={len(rounds)}, deleted={counts}, '
              f'remaining teams and progress={remaining}, admins preserved={admins_before}')


def downgrade():
    # Deleted player data must not be recreated by an application rollback.
    pass
