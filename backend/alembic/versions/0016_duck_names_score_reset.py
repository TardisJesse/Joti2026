"""Remove duck name numbers and apply the requested one-time score reset."""
import re
import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CapturePoint, Game, GameObject, ObjectType, ScoreEvent, ScoreType, Team

revision = '0016_duck_names_score_reset'
down_revision = '0015_scanner_rewards'
branch_labels = None
depends_on = None


def upgrade():
    with Session(bind=op.get_bind(), join_transaction_mode='create_savepoint') as db:
        # Gameplay and clock updates use these same locks. Reset every round once,
        # preserving original rewards, claims, teams and the score audit history.
        db.query(Game).order_by(Game.id).with_for_update().all()
        renamed = 0
        for obj in db.query(GameObject).filter_by(type=ObjectType.PHYSICAL_DUCK):
            name = re.sub(r'^Eend\s+\d+\s*[·:—-]\s*', '', obj.name)
            if name != obj.name:
                obj.name = name
                renamed += 1

        totals = db.query(Team.id, func.sum(ScoreEvent.points)).join(
            ScoreEvent, ScoreEvent.team_id == Team.id
        ).group_by(Team.id).all()
        reset_count = 0
        for team_id, total in totals:
            if total:
                db.add(ScoreEvent(
                    team_id=team_id, type=ScoreType.ADMIN_ADJUSTMENT,
                    points=-total,
                    reference_id=str(uuid.uuid5(uuid.NAMESPACE_URL, '0016:score-reset:' + team_id)),
                    note='Alle teamscores op verzoek van de spelleiding teruggezet naar nul.',
                ))
                reset_count += 1

        # Pending ownership income from before this reset must not reappear.
        at = datetime.now(timezone.utc)
        db.query(CapturePoint).update({
            'income_updated_at': at, 'income_remainder_seconds': 0,
        })
        db.flush()
        nonzero = db.query(ScoreEvent.team_id).group_by(ScoreEvent.team_id).having(
            func.sum(ScoreEvent.points) != 0
        ).count()
        if nonzero:
            raise RuntimeError('Score reset did not reach zero for every team')
        db.commit()
        print(f'Duck names updated: {renamed}; teams reset: {reset_count}; nonzero scores: {nonzero}')


def downgrade():
    # A later rollback must not silently resurrect scores that were cleared.
    pass
