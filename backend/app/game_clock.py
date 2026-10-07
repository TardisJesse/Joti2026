from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .capture_income import settle_capture_income, utc
from .models import CapturePoint, Game, GameObject, GameStatus
from .services import capture_started


def game_dto(game: Game) -> dict:
    return {'id': game.id, 'code': game.game_code, 'name': game.name,
            'status': game.status, 'ends_at': utc(game.ends_at).isoformat() if game.ends_at else None,
            'timer_remaining_seconds': game.timer_remaining_seconds,
            'server_now': datetime.now(timezone.utc).isoformat()}


def expire_game(db: Session, game: Game, at: datetime | None = None) -> bool:
    at = at or datetime.now(timezone.utc)
    if game.status != GameStatus.RUNNING or not game.ends_at or utc(game.ends_at) > at:
        return False
    game = db.query(Game).filter_by(id=game.id).populate_existing().with_for_update().one()
    if game.status != GameStatus.RUNNING or not game.ends_at or utc(game.ends_at) > at:
        return False
    settle_capture_income(db, game.id, at)
    game.status = GameStatus.FINISHED
    game.timer_remaining_seconds = None
    point_ids = {point.id for point in db.query(CapturePoint).join(GameObject, CapturePoint.game_object_id == GameObject.id).filter(GameObject.game_id == game.id)}
    for key in list(capture_started):
        if key[0] in point_ids:
            capture_started.pop(key, None)
    db.flush()
    return True


def expire_due_games(session_factory, at: datetime | None = None) -> list[dict]:
    """Run without a browser and recover overdue deadlines after a restart."""
    at = at or datetime.now(timezone.utc)
    with session_factory() as db:
        ids = [game_id for (game_id,) in db.query(Game.id).filter(Game.status == GameStatus.RUNNING, Game.ends_at <= at)]
    finished = []
    for game_id in ids:
        with session_factory() as db:
            game = db.get(Game, game_id)
            if game and expire_game(db, game, at):
                db.commit()
                finished.append(game_dto(game))
    return finished
