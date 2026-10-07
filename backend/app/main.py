import asyncio, logging, math, os, time
from contextlib import suppress
from .game_clock import expire_due_games, expire_game, game_dto
from .capture_income import settle_capture_income
from .images import normalize_image
from .team_colors import next_team_color
from .services import capture_started
from datetime import datetime, timedelta, timezone
from .capture_income import utc
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from .push import router as push_router, notify_capture
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .database import SessionLocal, db_session
from .models import *
from .schemas import (AnswerInput, GameCreateInput, GameJoinInput, GameObjectInput,
                      GameStatusInput, GameTimerInput, LocationInput, LoginInput, ScanInput, ImageInput)
from .security import create_token, current_user, hash_password, require_admin, verify_password
from .services import (begin_capture, broadcast, cancel_capture, complete_capture, get_location,
                       hash_token, require_nearby, set_location, subscribers)

app = FastAPI(title="CyberJoti API", version="0.1.0")
app.include_router(push_router)
app.add_middleware(CORSMiddleware, allow_origins=settings().cors_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


async def round_clock_loop():
    while True:
        try:
            finished = await asyncio.to_thread(expire_due_games, SessionLocal)
            for game in finished:
                await broadcast(f"game:{game['id']}:events", {'type': 'GAME_UPDATED', 'data': game})
        except Exception:
            logging.getLogger(__name__).exception('Round timer check failed')
        await asyncio.sleep(1)


@app.on_event('startup')
async def start_round_clock():
    app.state.round_clock = asyncio.create_task(round_clock_loop())


@app.on_event('shutdown')
async def stop_round_clock():
    task = getattr(app.state, 'round_clock', None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@app.on_event("startup")
def bootstrap_admin_from_environment() -> None:
    """Create or reset an explicitly configured MVP admin after migrations run."""
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    if not username or not password:
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(func.lower(User.name) == username.lower()).first()
        if user is None:
            db.add(User(name=username, role=UserRole.ADMIN, password_hash=hash_password(password)))
        else:
            user.name = username
            user.role = UserRole.ADMIN
            user.active = True
            user.password_hash = hash_password(password)
        db.commit()
    finally:
        db.close()

def dto_user(user: User, db: Session | None = None):
    result = {"id": user.id, "name": user.name, "role": user.role, "team_id": user.team_id, "profile_image": user.profile_image}
    if db and user.team_id:
        team = db.get(Team, user.team_id)
        if team: result.update({"team_name": team.name, "game_id": team.game_id})
    return result


def team_game(user: User, db: Session) -> Game:
    if not user.team_id:
        raise HTTPException(403, "This action requires a team")
    team = db.get(Team, user.team_id)
    game = db.get(Game, team.game_id) if team else None
    if not game:
        raise HTTPException(404, "Game round not found")
    if expire_game(db, game): db.commit()
    return game


def selected_game(user: User, db: Session, game_id: str | None = None) -> Game:
    if user.role != UserRole.ADMIN:
        return team_game(user, db)
    if not game_id:
        raise HTTPException(422, "Select a game round first")
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(404, "Game round not found")
    if expire_game(db, game): db.commit()
    return game


def require_running(game: Game) -> None:
    if game.status == GameStatus.FINISHED or (game.status == GameStatus.RUNNING and game.ends_at and utc(game.ends_at) <= datetime.now(timezone.utc)):
        raise HTTPException(409, 'Deze spelronde is afgelopen')
    if game.status != GameStatus.RUNNING:
        raise HTTPException(409, "This game round has not started yet")


def object_for(object_id: str, expected: ObjectType, user: User, db: Session):
    obj = db.get(GameObject, object_id)
    if not obj or not obj.active or obj.type != expected: raise HTTPException(404, "Game object not found")
    game = team_game(user, db)
    if obj.game_id != game.id:
        raise HTTPException(404, "Game object not found")
    game = db.query(Game).filter_by(id=game.id).populate_existing().with_for_update().one()
    require_running(game)
    return obj
def require_team(user: User):
    if not user.team_id: raise HTTPException(403, "This action requires a team")

@app.get("/health")
def health(): return {"status": "ok", "time": datetime.now(timezone.utc)}

@app.post("/api/auth/login")
def login(payload: LoginInput, db: Session = Depends(db_session)):
    user = db.query(User).filter(func.lower(User.name) == payload.name.lower()).first()
    if not user or not user.active or not verify_password(payload.password, user.password_hash): raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": dto_user(user, db)}
@app.post("/api/auth/logout")
def logout(user: User = Depends(current_user)): return {"ok": True}
@app.get("/api/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(db_session)): return dto_user(user, db)

@app.put('/api/profile/image')
async def profile_image(payload: ImageInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    user.profile_image = normalize_image(payload.image)
    db.commit()
    if user.team_id:
        game = team_game(user, db)
        await broadcast(f'game:{game.id}:events', {'type': 'PROFILE_UPDATED', 'data': {'team_id': user.team_id}})
    return dto_user(user, db)


@app.post("/api/games/join")
def join_game(payload: GameJoinInput, db: Session = Depends(db_session)):
    code = payload.game_code.strip().upper()
    team_name = payload.team_name.strip()
    game = db.query(Game).filter(func.lower(Game.game_code) == code.lower()).with_for_update().first()
    if game is None:
        raise HTTPException(404, "Unknown game code. Ask an admin to create the game round.")
    if expire_game(db, game): db.commit()
    if game.status == GameStatus.FINISHED:
        raise HTTPException(409, "This game round has finished")
    if db.query(Team).filter(Team.game_id == game.id, func.lower(Team.name) == team_name.lower()).first():
        raise HTTPException(409, "This team name is already active in this game round")
    team = Team(game_id=game.id, name=team_name, color=next_team_color(color for (color,) in db.query(Team.color).filter_by(game_id=game.id).all()))
    db.add(team); db.flush()
    player = User(name=f"team-{team.id}", team_id=team.id, role=UserRole.TEAM_LEADER, password_hash=hash_password(os.urandom(24).hex()))
    db.add(player); db.commit()
    return {"access_token": create_token(player), "token_type": "bearer", "user": dto_user(player, db), "game": game_dto(game)}


@app.get('/api/game')
def current_game(game_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(db_session)):
    return game_dto(selected_game(user, db, game_id))


@app.get("/api/admin/games")
def admin_games(admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    games = db.query(Game).order_by(Game.created_at.desc()).all()
    for game in games:
        if expire_game(db, game): db.commit()
    return [game_dto(game) for game in games]


@app.post("/api/admin/games")
def create_game(payload: GameCreateInput, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    code = payload.game_code.strip().upper()
    if db.query(Game).filter(func.lower(Game.game_code) == code.lower()).first():
        raise HTTPException(409, "This game code already exists")
    game = Game(game_code=code, name=payload.name or f"Spelronde {code}", status=GameStatus.READY)
    db.add(game); db.commit()
    return game_dto(game)


@app.put("/api/admin/games/{game_id}/status")
def set_game_status(game_id: str, payload: GameStatusInput, admin: User = Depends(require_admin), db: Session = Depends(db_session), background_tasks: BackgroundTasks = None):
    game = selected_game(admin, db, game_id)
    try: status = GameStatus(payload.status)
    except ValueError: raise HTTPException(422, "Unknown game status")
    if not game: raise HTTPException(404, "Game round not found")
    if game.status == GameStatus.FINISHED and status == GameStatus.PAUSED:
        raise HTTPException(409, 'Deze spelronde is al afgelopen')
    at = settle_capture_income(db, game.id)
    if game.status != status:
        if status == GameStatus.PAUSED and game.ends_at and game.status == GameStatus.RUNNING:
            game.timer_remaining_seconds = max(0, math.ceil((utc(game.ends_at) - at).total_seconds()))
            game.ends_at = None
        elif status == GameStatus.RUNNING and game.timer_remaining_seconds:
            game.ends_at = at + timedelta(seconds=game.timer_remaining_seconds)
            game.timer_remaining_seconds = None
        elif status != GameStatus.RUNNING:
            game.ends_at = None; game.timer_remaining_seconds = None
        elif game.status == GameStatus.FINISHED:
            game.ends_at = None
    game.status = status; db.commit()
    if background_tasks:
        background_tasks.add_task(broadcast, f'game:{game.id}:events', {'type': 'GAME_UPDATED', 'data': game_dto(game)})
    return game_dto(game)


@app.put('/api/admin/games/{game_id}/timer')
async def set_round_timer(game_id: str, payload: GameTimerInput, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    game = selected_game(admin, db, game_id)
    at = settle_capture_income(db, game.id)
    game.ends_at = at + timedelta(seconds=payload.duration_seconds)
    game.timer_remaining_seconds = None
    game.starts_at = game.starts_at or at
    game.status = GameStatus.RUNNING
    db.commit()
    result = game_dto(game)
    await broadcast(f'game:{game.id}:events', {'type': 'GAME_UPDATED', 'data': result})
    return result


@app.delete('/api/admin/games/{game_id}/timer')
async def remove_round_timer(game_id: str, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    game = selected_game(admin, db, game_id)
    settle_capture_income(db, game.id)
    game.ends_at = None; game.timer_remaining_seconds = None
    db.commit()
    result = game_dto(game)
    await broadcast(f'game:{game.id}:events', {'type': 'GAME_UPDATED', 'data': result})
    return result

@app.post("/api/location")
async def location(payload: LocationInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    game = team_game(user, db)
    server_time = datetime.now(timezone.utc).isoformat()
    value = {"lat": payload.latitude, "lng": payload.longitude, "accuracy": payload.accuracy, "updated_at": server_time}
    set_location(user.id, value)
    await broadcast(f"team:{user.team_id}", {"type": "PLAYER_LOCATION", "data": {"player_id": user.id, **value}})
    await broadcast(f"game:{game.id}:admin", {"type": "PLAYER_LOCATION", "data": {"player_id": user.id, "team_id": user.team_id, **value}})
    return {"ok": True, "updated_at": server_time}

@app.get("/api/locations")
def locations(game_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(db_session)):
    game = selected_game(user, db, game_id)
    query = db.query(User).join(Team, User.team_id == Team.id).filter(Team.game_id == game.id, User.active.is_(True))
    if user.role != UserRole.ADMIN: query = query.filter(User.id == user.id)
    return [{"player_id": player.id, "name": player.name, "team_name": db.get(Team, player.team_id).name, "profile_image": player.profile_image, "team_id": player.team_id, "location": get_location(player.id)} for player in query.all() if get_location(player.id)]

@app.get("/api/game-objects")
def game_objects(game_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(db_session)):
    game = selected_game(user, db, game_id)
    rows = db.query(GameObject, CapturePoint, Team).outerjoin(CapturePoint, CapturePoint.game_object_id == GameObject.id).outerjoin(Team, Team.id == CapturePoint.owner_team_id).filter(GameObject.game_id == game.id, GameObject.active.is_(True)).all()
    return [{"id": x.id, "type": x.type, "name": x.name, "description": x.description, "latitude": x.latitude, "longitude": x.longitude, "activation_radius_meters": x.activation_radius_meters, "capture_seconds": point.capture_seconds if point else None, "points_per_minute": point.points_per_minute if point else None, "owner_team_id": owner.id if owner else None, "owner_team_name": owner.name if owner else None, "owner_team_color": owner.color if owner else None} for x, point, owner in rows]
@app.get("/api/game-objects/{object_id}")
def game_object(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    obj = db.get(GameObject, object_id)
    if not obj or obj.game_id != team_game(user, db).id: raise HTTPException(404, "Game object not found")
    result = {"id": obj.id, "type": obj.type, "name": obj.name, "description": obj.description, "activation_radius_meters": obj.activation_radius_meters}
    if obj.type == ObjectType.PUZZLE:
        puzzle = db.query(Puzzle).filter_by(game_object_id=obj.id).one(); result["question"] = puzzle.question
    return result

@app.post("/api/admin/game-objects")
async def create_game_object(payload: GameObjectInput, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    """Create an active game object and its authoritative activity configuration."""
    try: object_type = ObjectType(payload.type)
    except ValueError: raise HTTPException(422, "Unknown game object type")
    game = selected_game(admin, db, payload.game_id)
    if object_type == ObjectType.PUZZLE and (not payload.question or not payload.answer):
        raise HTTPException(422, "A puzzle needs both a question and answer")
    obj = GameObject(game_id=game.id, type=object_type, name=payload.name, description=payload.description,
                     latitude=payload.latitude, longitude=payload.longitude,
                     activation_radius_meters=payload.activation_radius_meters)
    db.add(obj); db.flush()
    response: dict = {"id": obj.id, "type": obj.type, "name": obj.name, "latitude": obj.latitude, "longitude": obj.longitude}
    if object_type == ObjectType.PUZZLE:
        db.add(Puzzle(game_object_id=obj.id, question=payload.question or "", answer_hash=hash_password((payload.answer or "").strip().lower()), reward_points=payload.reward_points, max_attempts=payload.max_attempts))
    elif object_type == ObjectType.CAPTURE_POINT:
        db.add(CapturePoint(game_object_id=obj.id, capture_seconds=payload.capture_seconds, cooldown_seconds=payload.cooldown_seconds, capture_reward=payload.reward_points, points_per_minute=payload.points_per_minute))
    elif object_type == ObjectType.PHOTO_POINT:
        db.add(PhotoPoint(game_object_id=obj.id, reward_points=payload.reward_points))
    else:
        # A random token is returned once so the organiser can write it to an NFC tag.
        import secrets
        token = secrets.token_urlsafe(24); db.add(Duck(game_object_id=obj.id, scan_token_hash=hash_token(token), reward_points=payload.reward_points, search_radius_meters=payload.search_radius_meters)); response["scan_token"] = token
    db.commit()
    await broadcast(f"game:{game.id}:events", {"type": "OBJECT_UPDATED", "data": {"id": obj.id}})
    return response

@app.delete("/api/admin/game-objects/{object_id}")
async def delete_game_object(object_id: str, game_id: str, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    obj = db.get(GameObject, object_id)
    game = selected_game(admin, db, game_id)
    if not obj or obj.game_id != game.id: raise HTTPException(404, "Game object not found")
    settle_capture_income(db, game.id)
    obj.active = False; db.commit()
    await broadcast(f"game:{game.id}:events", {"type": "OBJECT_UPDATED", "data": {"id": object_id, "active": False}})
    return {"ok": True}

@app.post("/api/puzzles/{object_id}/answer")
async def answer(object_id: str, payload: AnswerInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.PUZZLE, user, db); require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    puzzle = db.query(Puzzle).filter_by(game_object_id=obj.id).one()
    solved = db.query(ScoreEvent).filter_by(team_id=user.team_id, type=ScoreType.PUZZLE_SOLVED, reference_id=puzzle.id).first()
    if solved: raise HTTPException(409, "Your team already solved this puzzle")
    attempts = db.query(PuzzleAttempt).filter_by(puzzle_id=puzzle.id, team_id=user.team_id).count()
    if puzzle.max_attempts is not None and attempts >= puzzle.max_attempts: raise HTTPException(429, "Maximum attempts reached")
    correct = verify_password(payload.answer.strip().lower(), puzzle.answer_hash)
    require_running(db.get(Game, obj.game_id))
    db.add(PuzzleAttempt(puzzle_id=puzzle.id, team_id=user.team_id, user_id=user.id, correct=correct))
    if correct: db.add(ScoreEvent(team_id=user.team_id, type=ScoreType.PUZZLE_SOLVED, points=puzzle.reward_points, reference_id=puzzle.id))
    db.commit()
    if correct: await broadcast(f"team:{user.team_id}", {"type": "SCORE_UPDATED", "data": {"team_id": user.team_id}})
    return {"correct": correct, "points": puzzle.reward_points if correct else 0}

@app.post("/api/capture/{object_id}/start")
async def capture_start(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.CAPTURE_POINT, user, db); require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    point = db.query(CapturePoint).filter_by(game_object_id=obj.id).one(); started = begin_capture(point.id, user.team_id, point.cooldown_seconds)
    db.add(CaptureEvent(capture_point_id=point.id, team_id=user.team_id, user_id=user.id, event="STARTED")); db.commit()
    await broadcast(f"team:{user.team_id}", {"type": "CAPTURE_STARTED", "data": {"object_id": object_id, "started_at": started}})
    return {"started": True, "capture_seconds": point.capture_seconds, "remaining_seconds": max(0, point.capture_seconds - (time.monotonic() - started))}
@app.post("/api/capture/{object_id}/cancel")
async def capture_cancel(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.CAPTURE_POINT, user, db); point = db.query(CapturePoint).filter_by(game_object_id=obj.id).one(); cancel_capture(point.id, user.team_id)
    db.add(CaptureEvent(capture_point_id=point.id, team_id=user.team_id, user_id=user.id, event="CANCELLED")); db.commit(); return {"cancelled": True}
@app.get("/api/capture/{object_id}/status")
async def capture_status(object_id: str, background_tasks: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.CAPTURE_POINT, user, db)
    income_time = settle_capture_income(db, obj.game_id)
    require_running(db.get(Game, obj.game_id))
    point = db.query(CapturePoint).filter_by(game_object_id=obj.id).one()
    try: require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    except HTTPException: cancel_capture(point.id, user.team_id); db.commit(); return {"state": "CANCELLED", "owner_team_id": point.owner_team_id}
    started = capture_started.get((point.id, user.team_id))
    if started is None: db.commit(); return {"state": "IDLE", "owner_team_id": point.owner_team_id}
    if complete_capture(point.id, user.team_id, point.capture_seconds, point.cooldown_seconds):
        require_running(db.get(Game, obj.game_id))
        if point.owner_team_id != user.team_id:
            point.income_remainder_seconds = 0
        point.income_updated_at = income_time
        point.owner_team_id = user.team_id; db.add(CaptureEvent(capture_point_id=point.id, team_id=user.team_id, user_id=user.id, event="COMPLETED")); db.add(ScoreEvent(team_id=user.team_id, type=ScoreType.CAPTURE_COMPLETED, points=point.capture_reward, reference_id=os.urandom(16).hex())); db.commit()
        owner = db.get(Team, user.team_id)
        background_tasks.add_task(notify_capture, obj.game_id, obj.name, owner.name)
        await broadcast(f"game:{obj.game_id}:events", {"type": "CAPTURE_COMPLETED", "data": {"object_id": object_id, "object_name": obj.name, "owner_team_id": owner.id, "owner_team_name": owner.name, "owner_team_color": owner.color}})
        return {"state": "COMPLETED", "owner_team_id": user.team_id}
    db.commit()
    return {"state": "CAPTURING", "owner_team_id": point.owner_team_id, "capture_seconds": point.capture_seconds, "remaining_seconds": max(0, point.capture_seconds - (time.monotonic() - started))}

@app.get('/api/photos/{object_id}')
def photos(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    obj = db.get(GameObject, object_id)
    if not obj or not obj.active or obj.type != ObjectType.PHOTO_POINT:
        raise HTTPException(404, 'Photo point not found')
    if user.role != UserRole.ADMIN:
        if obj.game_id != team_game(user, db).id:
            raise HTTPException(404, 'Photo point not found')
        require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    point = db.query(PhotoPoint).filter_by(game_object_id=obj.id).one()
    rows = db.query(PhotoSubmission, Team).join(Team, Team.id == PhotoSubmission.team_id).filter(PhotoSubmission.photo_point_id == point.id).order_by(PhotoSubmission.created_at.desc()).all()
    return {'reward_points': point.reward_points, 'submitted': any(photo.team_id == user.team_id for photo, team in rows), 'photos': [{'id': photo.id, 'team_name': team.name, 'image': photo.image} for photo, team in rows]}

@app.post('/api/photos/{object_id}')
async def submit_photo(object_id: str, payload: ImageInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    obj = object_for(object_id, ObjectType.PHOTO_POINT, user, db)
    require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    point = db.query(PhotoPoint).filter_by(game_object_id=obj.id).one()
    image = normalize_image(payload.image)
    require_running(db.get(Game, obj.game_id))
    try:
        db.add(PhotoSubmission(photo_point_id=point.id, team_id=user.team_id, user_id=user.id, image=image))
        db.flush()
        db.add(ScoreEvent(team_id=user.team_id, type=ScoreType.PHOTO_SUBMITTED, reference_id=point.id, points=point.reward_points))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Your team already submitted a photo at this point')
    await broadcast(f'game:{obj.game_id}:events', {'type': 'SCORE_UPDATED', 'data': {'team_id': user.team_id}})
    return {'points': point.reward_points}

@app.post("/api/ducks/scan")
async def duck_scan(payload: ScanInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); duck = db.query(Duck).filter_by(scan_token_hash=hash_token(payload.token)).first()
    if not duck: raise HTTPException(404, "Unknown duck token")
    obj = db.get(GameObject, duck.game_object_id)
    game = team_game(user, db)
    if not obj or obj.game_id != game.id: raise HTTPException(404, "Unknown duck token")
    require_running(game)
    require_nearby(user.id, obj.latitude, obj.longitude, duck.search_radius_meters)
    require_running(game)
    try:
        db.add(DuckScan(duck_id=duck.id, team_id=user.team_id, user_id=user.id)); db.flush(); db.add(ScoreEvent(team_id=user.team_id, type=ScoreType.DUCK_FOUND, points=duck.reward_points, reference_id=duck.id)); db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Your team already scanned this duck")
    await broadcast(f"team:{user.team_id}", {"type": "SCORE_UPDATED", "data": {"team_id": user.team_id}})
    return {"found": True, "name": obj.name, "points": duck.reward_points}

@app.get("/api/scores")
def scores(game_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(db_session)):
    game = selected_game(user, db, game_id)
    settle_capture_income(db, game.id); db.commit()
    total = func.coalesce(func.sum(ScoreEvent.points), 0)
    rows = db.query(Team.id, Team.name, Team.color, total.label("score")).outerjoin(ScoreEvent, ScoreEvent.team_id == Team.id).filter(Team.game_id == game.id).group_by(Team.id, Team.name, Team.color).order_by(total.desc(), func.lower(Team.name), Team.id).all()
    portraits = {}
    for player in db.query(User).join(Team, User.team_id == Team.id).filter(Team.game_id == game.id, User.active.is_(True), User.profile_image.isnot(None)).order_by(User.created_at, User.id):
        portraits.setdefault(player.team_id, player.profile_image)
    return [{"team_id": r.id, "name": r.name, "color": r.color, "score": r.score, "profile_image": portraits.get(r.id)} for r in rows]

@app.websocket("/ws/game")
async def websocket(websocket: WebSocket):
    # Browser clients pass their bearer token as ?token=; invalid tokens never join a channel.
    from jwt import decode, PyJWTError
    token = websocket.query_params.get("token")
    try: user_id = decode(token, settings().secret_key, algorithms=["HS256"])["sub"]
    except (PyJWTError, KeyError): await websocket.close(code=4401); return
    db = next(db_session()); user = db.get(User, user_id)
    if not user: await websocket.close(code=4401); return
    game_id = websocket.query_params.get("game_id")
    try: game = selected_game(user, db, game_id)
    except HTTPException: db.close(); await websocket.close(code=4403); return
    db.close()
    channel = f"game:{game.id}:admin" if user.role == UserRole.ADMIN else f"team:{user.team_id}"
    queue: asyncio.Queue = asyncio.Queue(); subscribers[channel].add(queue); subscribers[f"game:{game.id}:events"].add(queue); await websocket.accept()
    try:
        while True:
            try: event = await asyncio.wait_for(queue.get(), timeout=25); await websocket.send_json(event)
            except asyncio.TimeoutError: await websocket.send_json({"type": "HEARTBEAT"})
    except WebSocketDisconnect: pass
    finally:
        subscribers[channel].discard(queue)
        subscribers[f"game:{game.id}:events"].discard(queue)
