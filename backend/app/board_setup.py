"""Install the reviewed Allart boards once, preserving players and scoring history."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .models import BoardInstallation, CapturePoint, Game, GameObject, GameStatus, ObjectType, PhotoPoint, Puzzle
from .capture_income import settle_capture_income, utc
from .news import add_news

PACK_FILE = Path(__file__).parent / 'data' / 'allart_joti_2026_v1.json'


def normalized(value):
    value = ''.join(char for char in (value or '').casefold() if char.isalnum())
    return value.removeprefix('spelronde')


def install_boards(db, pack=None):
    pack = pack or json.loads(PACK_FILE.read_text(encoding='utf-8'))
    results = []
    for board in pack['boards']:
        key = normalized(board['code'])
        games = db.query(Game).all()
        matching = [game for game in games if normalized(game.game_code) == key]
        if not matching:
            matching = [game for game in games if normalized(game.name) == key]
        if len(matching) > 1:
            raise ValueError(f"Ambiguous game round: {board['name']}")
        if matching:
            game = db.query(Game).filter_by(id=matching[0].id).with_for_update().one()
        else:
            game = Game(game_code=board['code'], name=board['name'], status=GameStatus.READY)
            db.add(game); db.flush()
        if db.query(BoardInstallation).filter_by(game_id=game.id, version=pack['version']).first():
            results.append({'round': game.name, 'skipped': True}); continue
        snapshot = {'name': game.name, 'status': game.status.value, 'play_area_json': game.play_area_json,
                    'ends_at': utc(game.ends_at).isoformat() if game.ends_at else None,
                    'timer_remaining_seconds': game.timer_remaining_seconds,
                    'bonus_elapsed_seconds': game.bonus_elapsed_seconds,
                    'bonus_updated_at': utc(game.bonus_updated_at).isoformat() if game.bonus_updated_at else None,
                    'active_object_ids': [obj.id for obj in db.query(GameObject).filter_by(game_id=game.id, active=True)]}
        settle_capture_income(db, game.id)
        snapshot['bonus_elapsed_seconds'] = game.bonus_elapsed_seconds
        for obj in db.query(GameObject).filter_by(game_id=game.id, active=True): obj.active = False
        ids = []
        for point in board['objects']:
            obj = db.get(GameObject, point['id'])
            if obj and obj.game_id != game.id: raise ValueError('Board object belongs to another round')
            if not obj:
                obj = GameObject(id=point['id'], game_id=game.id); db.add(obj)
            for field in ('name', 'description', 'latitude', 'longitude', 'activation_radius_meters'):
                setattr(obj, field, point[field])
            obj.type = ObjectType(point['type']); obj.active = True
            db.flush(); ids.append(obj.id)
            if obj.type == ObjectType.CAPTURE_POINT:
                capture = db.query(CapturePoint).filter_by(game_object_id=obj.id).first()
                if not capture: capture = CapturePoint(game_object_id=obj.id); db.add(capture)
                for field in ('capture_seconds', 'cooldown_seconds', 'points_per_minute'):
                    setattr(capture, field, point[field])
                capture.capture_reward = point['reward_points']; capture.owner_team_id = None
                capture.income_updated_at = datetime.now(timezone.utc); capture.income_remainder_seconds = 0
            elif obj.type == ObjectType.PHOTO_POINT:
                photo = db.query(PhotoPoint).filter_by(game_object_id=obj.id).first()
                if not photo: photo = PhotoPoint(game_object_id=obj.id); db.add(photo)
                photo.reward_points = point['reward_points']
            elif obj.type == ObjectType.PUZZLE:
                puzzle = db.query(Puzzle).filter_by(game_object_id=obj.id).first()
                if not puzzle: puzzle = Puzzle(game_object_id=obj.id); db.add(puzzle)
                puzzle.question = point['question']; puzzle.answer_hash = point['answer_hash']
                puzzle.reward_points = point['reward_points']; puzzle.max_attempts = point['max_attempts']
            elif obj.type != ObjectType.SCANNER_POINT:
                raise ValueError('This board contains an unsupported activity')
        game.name = board['name']; game.status = GameStatus.READY
        if pack.get('play_area'): game.play_area_json = json.dumps(pack['play_area'])
        game.ends_at = None; game.timer_remaining_seconds = None
        game.bonus_elapsed_seconds = 0; game.bonus_updated_at = None
        db.add(BoardInstallation(game_id=game.id, version=pack['version'], snapshot_json=json.dumps(snapshot), object_ids_json=json.dumps(ids)))
        add_news(db, game.id, 'BOARD_READY', f"Het JOTI-spelbord voor {board['name']} staat klaar: {len(ids)} spelpunten. De beheerder kan de ronde starten.", source_key=f"board:{pack['version']}")
        db.flush()
        results.append({'round': game.name, 'code': game.game_code, 'objects': len(ids), 'retired': len(snapshot['active_object_ids'])})
    return results


def restore_boards(db, version):
    for record in db.query(BoardInstallation).filter_by(version=version).all():
        snapshot = json.loads(record.snapshot_json)
        for obj in db.query(GameObject).filter(GameObject.id.in_(json.loads(record.object_ids_json))): obj.active = False
        for obj in db.query(GameObject).filter(GameObject.id.in_(snapshot['active_object_ids'])):
            obj.active = True
            capture = db.query(CapturePoint).filter_by(game_object_id=obj.id).first()
            if capture: capture.income_updated_at = datetime.now(timezone.utc)
        game = db.get(Game, record.game_id)
        game.play_area_json = snapshot.get('play_area_json')
        for field in ('name', 'timer_remaining_seconds', 'bonus_elapsed_seconds'):
            setattr(game, field, snapshot[field])
        game.status = GameStatus(snapshot['status'])
        for field in ('ends_at', 'bonus_updated_at'):
            setattr(game, field, datetime.fromisoformat(snapshot[field]) if snapshot[field] else None)
        if game.bonus_updated_at: game.bonus_updated_at = datetime.now(timezone.utc)
    db.flush()
