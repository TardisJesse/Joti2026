import uuid
from datetime import datetime, timezone
from .bonus import bonus_state, utc
from .models import Game, GameStatus, GameObject, CapturePoint, NewsEvent


def news_dto(row):
    return {'id': row.id, 'game_id': row.game_id, 'kind': row.kind, 'message': row.message,
            'team_name': row.team_name, 'created_at': utc(row.created_at).isoformat()}


def add_news(db, game_id, kind, message, team_name=None, source_key=None, at=None):
    source_key = source_key or str(uuid.uuid4())
    if db.query(NewsEvent.id).filter_by(game_id=game_id, source_key=source_key).first():
        return
    row = NewsEvent(game_id=game_id, kind=kind, message=message, team_name=team_name,
                    source_key=source_key, created_at=at or datetime.now(timezone.utc))
    db.add(row); db.flush()
    return row


def collect_news(session_factory):
    """Discover current bonuses without players; clients recover missed events via HTTP."""
    with session_factory() as db:
        for game in db.query(Game).filter_by(status=GameStatus.RUNNING).with_for_update().all():
            ids = [row.id for row in db.query(GameObject).join(CapturePoint, CapturePoint.game_object_id == GameObject.id).filter(GameObject.game_id == game.id, GameObject.active.is_(True)).order_by(GameObject.id)]
            bonus = bonus_state(game, ids)
            if bonus:
                obj = db.get(GameObject, bonus['object_id'])
                add_news(db, game.id, 'BONUS_STARTED', f'{obj.name} is vijf minuten lang de bonuslocatie: dubbele volgers per minuut!', source_key=f"bonus:{bonus['cycle']}")
        rows = db.query(NewsEvent).filter_by(published=False).order_by(NewsEvent.created_at, NewsEvent.id).with_for_update(skip_locked=True).limit(100).all()
        events = [news_dto(row) for row in rows]
        for row in rows: row.published = True
        db.commit()
        return events
