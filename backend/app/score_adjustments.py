from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .bonus import utc
from .concurrency import database_worker
from .database import db_session
from .game_clock import expire_game
from .models import Game, GameStatus, ScoreEvent, ScoreType, Team, User
from .schemas import ScoreAdjustmentInput
from .security import require_admin
from .services import broadcast_from_worker

router = APIRouter(prefix='/api/admin/games')


def adjustment_dto(event, team_name, admin_name):
    actor, separator, reason = (event.note or '').partition('\n')
    return {'id': event.id, 'request_id': event.reference_id,
            'team_id': event.team_id, 'team_name': team_name, 'points': event.points,
            'reason': reason if separator else actor,
            'admin_id': actor if separator else None,
            'admin_name': admin_name or 'Spelleiding',
            'created_at': utc(event.created_at).isoformat()}


@router.get('/{game_id}/score-adjustments')
def score_adjustments(game_id: str, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    if not db.get(Game, game_id):
        raise HTTPException(404, 'Spelronde niet gevonden')
    rows = db.query(ScoreEvent, Team.name).join(Team, Team.id == ScoreEvent.team_id).filter(
        Team.game_id == game_id, ScoreEvent.type == ScoreType.ADMIN_ADJUSTMENT
    ).order_by(ScoreEvent.created_at.desc(), ScoreEvent.id.desc()).limit(200).all()
    actor_ids = {event.note.split('\n', 1)[0] for event, _ in rows if event.note and '\n' in event.note}
    actors = dict(db.query(User.id, User.name).filter(User.id.in_(actor_ids)).all()) if actor_ids else {}
    return [adjustment_dto(event, team_name, actors.get((event.note or '').split('\n', 1)[0])) for event, team_name in rows]


@router.put('/{game_id}/teams/{team_id}/score-adjustments/{request_id}')
@database_worker
def add_score_adjustment(game_id: str, team_id: str, request_id: UUID, payload: ScoreAdjustmentInput,
                         admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    game = db.query(Game).filter_by(id=game_id).populate_existing().with_for_update().first()
    if not game:
        raise HTTPException(404, 'Spelronde niet gevonden')
    team = db.query(Team).filter_by(id=team_id, game_id=game_id).first()
    if not team:
        raise HTTPException(404, 'Team niet gevonden in deze spelronde')

    reference = str(request_id)
    note = f'{admin.id}\n{payload.reason}'
    existing = db.query(ScoreEvent).filter_by(team_id=team_id, type=ScoreType.ADMIN_ADJUSTMENT, reference_id=reference).first()
    if existing:
        if existing.points != payload.points or existing.note != note:
            raise HTTPException(409, 'Deze correctie is al met andere gegevens verwerkt')
        return adjustment_dto(existing, team.name, admin.name)

    expire_game(db, game)
    if game.status != GameStatus.FINISHED:
        raise HTTPException(409, 'Punten rectificeren kan alleen na afloop van de spelronde')

    event = ScoreEvent(team_id=team_id, type=ScoreType.ADMIN_ADJUSTMENT,
                       points=payload.points, reference_id=reference, note=note)
    db.add(event)
    db.commit()
    result = adjustment_dto(event, team.name, admin.name)
    broadcast_from_worker(f'game:{game_id}:events', {'type': 'SCORE_UPDATED', 'data': {'team_id': team_id, 'adjustment_id': event.id}})
    return result
