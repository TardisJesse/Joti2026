import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import CapturePoint, Game, GameObject, GameStatus, ScoreEvent, ScoreType


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def settle_capture_income(db: Session, game_id: str, at: datetime | None = None) -> datetime:
    """Serialize ownership/round transitions and reads on the game row.

    Income is lazy-settled from a persistent clock, so it survives restarts and
    does not depend on browsers staying connected. Caller commits the transaction.
    """
    game = db.query(Game).filter_by(id=game_id).populate_existing().with_for_update().one()
    at = at or datetime.now(timezone.utc)
    # Never award ownership income beyond the authoritative round deadline.
    income_at = min(at, utc(game.ends_at)) if game.ends_at and game.status == GameStatus.RUNNING else at
    points = db.query(CapturePoint).join(GameObject, CapturePoint.game_object_id == GameObject.id).filter(GameObject.game_id == game_id).populate_existing().with_for_update().all()
    active_ids = {row.id for row in db.query(GameObject).filter_by(game_id=game_id, active=True)}
    for point in points:
        if point.owner_team_id and point.income_updated_at and game.status == GameStatus.RUNNING and point.game_object_id in active_ids:
            elapsed = max(0, (income_at - utc(point.income_updated_at)).total_seconds()) + point.income_remainder_seconds
            minutes = int(elapsed // 60)
            if minutes:
                reference = str(uuid.uuid5(uuid.NAMESPACE_URL, f'{point.id}:{point.income_updated_at.isoformat()}'))
                db.add(ScoreEvent(team_id=point.owner_team_id, type=ScoreType.CAPTURE_INCOME, points=minutes * point.points_per_minute, reference_id=reference, note=f'{minutes} minutes of capture ownership'))
            point.income_remainder_seconds = elapsed % 60
        point.income_updated_at = income_at
    db.flush()
    return at
