import asyncio, time
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .database import db_session
from .models import *
from .schemas import AnswerInput, GameObjectInput, LocationInput, LoginInput, ScanInput
from .security import create_token, current_user, hash_password, require_admin, verify_password
from .services import (begin_capture, broadcast, cancel_capture, complete_capture, get_location,
                       hash_token, require_nearby, set_location, subscribers)

app = FastAPI(title="CyberJoti API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings().cors_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def dto_user(user: User): return {"id": user.id, "name": user.name, "role": user.role, "team_id": user.team_id}
def active_game(db: Session):
    game = db.query(Game).filter(Game.status == GameStatus.RUNNING).first()
    if not game: raise HTTPException(409, "No game is currently running")
    return game
def object_for(object_id: str, expected: ObjectType, db: Session):
    obj = db.get(GameObject, object_id)
    if not obj or not obj.active or obj.type != expected: raise HTTPException(404, "Game object not found")
    active_game(db)
    return obj
def require_team(user: User):
    if not user.team_id: raise HTTPException(403, "This action requires a team")

@app.get("/health")
def health(): return {"status": "ok", "time": datetime.now(timezone.utc)}

@app.post("/api/auth/login")
def login(payload: LoginInput, db: Session = Depends(db_session)):
    user = db.query(User).filter(func.lower(User.name) == payload.name.lower()).first()
    if not user or not user.active or not verify_password(payload.password, user.password_hash): raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": dto_user(user)}
@app.post("/api/auth/logout")
def logout(user: User = Depends(current_user)): return {"ok": True}
@app.get("/api/auth/me")
def me(user: User = Depends(current_user)): return dto_user(user)

@app.post("/api/location")
async def location(payload: LocationInput, user: User = Depends(current_user)):
    require_team(user)
    server_time = datetime.now(timezone.utc).isoformat()
    value = {"lat": payload.latitude, "lng": payload.longitude, "accuracy": payload.accuracy, "updated_at": server_time}
    set_location(user.id, value)
    await broadcast(f"team:{user.team_id}", {"type": "PLAYER_LOCATION", "data": {"player_id": user.id, **value}})
    await broadcast("admin", {"type": "PLAYER_LOCATION", "data": {"player_id": user.id, "team_id": user.team_id, **value}})
    return {"ok": True, "updated_at": server_time}

@app.get("/api/locations")
def locations(user: User = Depends(current_user), db: Session = Depends(db_session)):
    query = db.query(User).filter(User.team_id.is_not(None), User.active.is_(True))
    if user.role != UserRole.ADMIN: query = query.filter(User.team_id == user.team_id)
    return [{"player_id": player.id, "name": player.name, "team_id": player.team_id, "location": get_location(player.id)} for player in query.all() if get_location(player.id)]

@app.get("/api/game-objects")
def game_objects(user: User = Depends(current_user), db: Session = Depends(db_session)):
    game = active_game(db)
    return [{"id": x.id, "type": x.type, "name": x.name, "description": x.description, "latitude": x.latitude, "longitude": x.longitude, "activation_radius_meters": x.activation_radius_meters} for x in db.query(GameObject).filter_by(game_id=game.id, active=True)]
@app.get("/api/game-objects/{object_id}")
def game_object(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    obj = db.get(GameObject, object_id)
    if not obj: raise HTTPException(404, "Game object not found")
    result = {"id": obj.id, "type": obj.type, "name": obj.name, "description": obj.description, "activation_radius_meters": obj.activation_radius_meters}
    if obj.type == ObjectType.PUZZLE:
        puzzle = db.query(Puzzle).filter_by(game_object_id=obj.id).one(); result["question"] = puzzle.question
    return result

@app.post("/api/admin/game-objects")
async def create_game_object(payload: GameObjectInput, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    """Create an active game object and its authoritative activity configuration."""
    try: object_type = ObjectType(payload.type)
    except ValueError: raise HTTPException(422, "Unknown game object type")
    game = active_game(db)
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
        db.add(CapturePoint(game_object_id=obj.id, capture_seconds=payload.capture_seconds, cooldown_seconds=payload.cooldown_seconds, capture_reward=payload.reward_points))
    else:
        # A random token is returned once so the organiser can write it to an NFC tag.
        import secrets
        token = secrets.token_urlsafe(24); db.add(Duck(game_object_id=obj.id, scan_token_hash=hash_token(token), reward_points=payload.reward_points, search_radius_meters=payload.search_radius_meters)); response["scan_token"] = token
    db.commit()
    await broadcast("admin", {"type": "OBJECT_UPDATED", "data": response})
    return response

@app.delete("/api/admin/game-objects/{object_id}")
async def delete_game_object(object_id: str, admin: User = Depends(require_admin), db: Session = Depends(db_session)):
    obj = db.get(GameObject, object_id)
    if not obj: raise HTTPException(404, "Game object not found")
    obj.active = False; db.commit()
    await broadcast("admin", {"type": "OBJECT_UPDATED", "data": {"id": object_id, "active": False}})
    return {"ok": True}

@app.post("/api/puzzles/{object_id}/answer")
async def answer(object_id: str, payload: AnswerInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.PUZZLE, db); require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    puzzle = db.query(Puzzle).filter_by(game_object_id=obj.id).one()
    solved = db.query(ScoreEvent).filter_by(team_id=user.team_id, type=ScoreType.PUZZLE_SOLVED, reference_id=puzzle.id).first()
    if solved: raise HTTPException(409, "Your team already solved this puzzle")
    attempts = db.query(PuzzleAttempt).filter_by(puzzle_id=puzzle.id, team_id=user.team_id).count()
    if puzzle.max_attempts is not None and attempts >= puzzle.max_attempts: raise HTTPException(429, "Maximum attempts reached")
    correct = verify_password(payload.answer.strip().lower(), puzzle.answer_hash)
    db.add(PuzzleAttempt(puzzle_id=puzzle.id, team_id=user.team_id, user_id=user.id, correct=correct))
    if correct: db.add(ScoreEvent(team_id=user.team_id, type=ScoreType.PUZZLE_SOLVED, points=puzzle.reward_points, reference_id=puzzle.id))
    db.commit()
    if correct: await broadcast(f"team:{user.team_id}", {"type": "SCORE_UPDATED", "data": {"team_id": user.team_id}})
    return {"correct": correct, "points": puzzle.reward_points if correct else 0}

@app.post("/api/capture/{object_id}/start")
async def capture_start(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.CAPTURE_POINT, db); require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    point = db.query(CapturePoint).filter_by(game_object_id=obj.id).one(); started = begin_capture(point.id, user.team_id, point.cooldown_seconds)
    db.add(CaptureEvent(capture_point_id=point.id, team_id=user.team_id, user_id=user.id, event="STARTED")); db.commit()
    await broadcast(f"team:{user.team_id}", {"type": "CAPTURE_STARTED", "data": {"object_id": object_id, "started_at": started}})
    return {"started": True, "capture_seconds": point.capture_seconds}
@app.post("/api/capture/{object_id}/cancel")
async def capture_cancel(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.CAPTURE_POINT, db); point = db.query(CapturePoint).filter_by(game_object_id=obj.id).one(); cancel_capture(point.id, user.team_id)
    db.add(CaptureEvent(capture_point_id=point.id, team_id=user.team_id, user_id=user.id, event="CANCELLED")); db.commit(); return {"cancelled": True}
@app.get("/api/capture/{object_id}/status")
async def capture_status(object_id: str, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); obj = object_for(object_id, ObjectType.CAPTURE_POINT, db); point = db.query(CapturePoint).filter_by(game_object_id=obj.id).one()
    try: require_nearby(user.id, obj.latitude, obj.longitude, obj.activation_radius_meters)
    except HTTPException: cancel_capture(point.id, user.team_id); return {"state": "CANCELLED", "owner_team_id": point.owner_team_id}
    if complete_capture(point.id, user.team_id, point.capture_seconds, point.cooldown_seconds):
        point.owner_team_id = user.team_id; db.add(CaptureEvent(capture_point_id=point.id, team_id=user.team_id, user_id=user.id, event="COMPLETED")); db.add(ScoreEvent(team_id=user.team_id, type=ScoreType.CAPTURE_COMPLETED, points=point.capture_reward, reference_id=f"{point.id}:{int(time.time())}")); db.commit()
        await broadcast(f"team:{user.team_id}", {"type": "CAPTURE_COMPLETED", "data": {"object_id": object_id}}); return {"state": "COMPLETED", "owner_team_id": user.team_id}
    return {"state": "CAPTURING", "owner_team_id": point.owner_team_id}

@app.post("/api/ducks/scan")
async def duck_scan(payload: ScanInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    require_team(user); duck = db.query(Duck).filter_by(scan_token_hash=hash_token(payload.token)).first()
    if not duck: raise HTTPException(404, "Unknown duck token")
    obj = db.get(GameObject, duck.game_object_id); active_game(db); require_nearby(user.id, obj.latitude, obj.longitude, duck.search_radius_meters)
    try:
        db.add(DuckScan(duck_id=duck.id, team_id=user.team_id, user_id=user.id)); db.flush(); db.add(ScoreEvent(team_id=user.team_id, type=ScoreType.DUCK_FOUND, points=duck.reward_points, reference_id=duck.id)); db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Your team already scanned this duck")
    await broadcast(f"team:{user.team_id}", {"type": "SCORE_UPDATED", "data": {"team_id": user.team_id}})
    return {"found": True, "name": obj.name, "points": duck.reward_points}

@app.get("/api/scores")
def scores(user: User = Depends(current_user), db: Session = Depends(db_session)):
    rows = db.query(Team.id, Team.name, Team.color, func.coalesce(func.sum(ScoreEvent.points), 0).label("score")).outerjoin(ScoreEvent, ScoreEvent.team_id == Team.id).group_by(Team.id).order_by(func.sum(ScoreEvent.points).desc()).all()
    return [{"team_id": r.id, "name": r.name, "color": r.color, "score": r.score} for r in rows]

@app.websocket("/ws/game")
async def websocket(websocket: WebSocket):
    # Browser clients pass their bearer token as ?token=; invalid tokens never join a channel.
    from jwt import decode, PyJWTError
    token = websocket.query_params.get("token")
    try: user_id = decode(token, settings().secret_key, algorithms=["HS256"])["sub"]
    except (PyJWTError, KeyError): await websocket.close(code=4401); return
    db = next(db_session()); user = db.get(User, user_id); db.close()
    if not user: await websocket.close(code=4401); return
    channel = "admin" if user.role == UserRole.ADMIN else f"team:{user.team_id}"
    queue: asyncio.Queue = asyncio.Queue(); subscribers[channel].add(queue); await websocket.accept()
    try:
        while True:
            try: event = await asyncio.wait_for(queue.get(), timeout=25); await websocket.send_json(event)
            except asyncio.TimeoutError: await websocket.send_json({"type": "HEARTBEAT"})
    except WebSocketDisconnect: pass
    finally: subscribers[channel].discard(queue)
