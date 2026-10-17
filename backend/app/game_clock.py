from datetime import datetime, timedelta, timezone
import json
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from .capture_income import settle_capture_income, utc
from .models import CapturePoint, Game, GameObject, GameStatus
from .services import capture_started
from .news import add_news


def game_dto(game: Game) -> dict:
    return {'id': game.id, 'code': game.game_code, 'name': game.name,
            'status': game.status, 'ends_at': utc(game.ends_at).isoformat() if game.ends_at else None,
            'scheduled_start_at': utc(game.scheduled_start_at).isoformat() if game.scheduled_start_at else None,
            'timer_remaining_seconds': game.timer_remaining_seconds,
            'play_area': json.loads(game.play_area_json) if game.play_area_json else None,
            'server_now': datetime.now(timezone.utc).isoformat()}


def start_due_game(db: Session, game: Game, at: datetime) -> bool:
    if game.status != GameStatus.READY or not game.scheduled_start_at or utc(game.scheduled_start_at) > at:
        return False
    game = db.query(Game).filter_by(id=game.id).populate_existing().with_for_update().one()
    if game.status != GameStatus.READY or not game.scheduled_start_at or utc(game.scheduled_start_at) > at:
        return False
    start = utc(game.scheduled_start_at)
    duration = game.timer_remaining_seconds
    if duration is None or duration < 60:
        raise ValueError('Scheduled round has no valid playing duration')
    # Anchor both clocks to the saved start, even after a restart or a late tick.
    # Preparation time never earns capture income or advances rotating bonuses.
    settle_capture_income(db, game.id, start)
    game.starts_at = start
    game.ends_at = start + timedelta(seconds=duration)
    game.timer_remaining_seconds = None
    game.scheduled_start_at = None
    game.status = GameStatus.RUNNING
    game.bonus_updated_at = start
    add_news(db, game.id, 'GAME_STATUS', 'De starttimer staat op nul. De spelronde is gestart!', at=start)
    db.flush()
    return True


def expire_game(db: Session, game: Game, at: datetime | None = None) -> bool:
    at = at or datetime.now(timezone.utc)
    if game.status != GameStatus.RUNNING or not game.ends_at or utc(game.ends_at) > at:
        return False
    game = db.query(Game).filter_by(id=game.id).populate_existing().with_for_update().one()
    if game.status != GameStatus.RUNNING or not game.ends_at or utc(game.ends_at) > at:
        return False
    settle_capture_income(db, game.id, at)
    game.status = GameStatus.FINISHED
    add_news(db, game.id, 'GAME_FINISHED', 'De spelronde is afgelopen. Bekijk de eindstand!', at=at)
    game.timer_remaining_seconds = None
    point_ids = {point.id for point in db.query(CapturePoint).join(GameObject, CapturePoint.game_object_id == GameObject.id).filter(GameObject.game_id == game.id)}
    for key in list(capture_started):
        if key[0] in point_ids:
            capture_started.pop(key, None)
    db.flush()
    return True


def advance_game(db: Session, game: Game, at: datetime | None = None) -> bool:
    at = at or datetime.now(timezone.utc)
    started = start_due_game(db, game, at)
    # If the server was offline for the whole round, finish it immediately too.
    finished = expire_game(db, game, at)
    return started or finished


def expire_due_games(session_factory, at: datetime | None = None) -> list[dict]:
    """Advance scheduled starts and end deadlines without an open browser."""
    at = at or datetime.now(timezone.utc)
    with session_factory() as db:
        ids = [game_id for (game_id,) in db.query(Game.id).filter(or_(
            and_(Game.status == GameStatus.RUNNING, Game.ends_at <= at),
            and_(Game.status == GameStatus.READY, Game.scheduled_start_at <= at),
        ))]
    changed = []
    for game_id in ids:
        with session_factory() as db:
            game = db.get(Game, game_id)
            if game and advance_game(db, game, at):
                db.commit()
                changed.append(game_dto(game))
    return changed
