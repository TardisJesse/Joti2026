from sqlalchemy.pool import StaticPool
import importlib.util
import json
from pathlib import Path
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Game, GameObject, ObjectType, Puzzle, Duck, PhotoPoint, CapturePoint, Team, ScoreEvent, ScoreType
from app.schemas import GameObjectInput

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('reward_balance', ROOT / 'alembic/versions/0014_reward_balance.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class RewardBalanceTests(unittest.TestCase):
    def test_templates_and_creation_defaults_have_requested_rewards(self):
        rewards = {'PHYSICAL_DUCK': 50, 'PHOTO_POINT': 20, 'PUZZLE': 20, 'CAPTURE_POINT': 5}
        for path in (ROOT / 'app/data').glob('allart_joti_2026_*.json'):
            for board in json.loads(path.read_text(encoding='utf-8'))['boards']:
                for obj in board['objects']:
                    if obj['type'] in rewards:
                        self.assertEqual(obj['reward_points'], rewards[obj['type']])
                    if obj['type'] == 'CAPTURE_POINT':
                        self.assertEqual(obj['points_per_minute'], 5)
        for kind, reward in rewards.items():
            payload = dict(game_id='0' * 36, type=kind, name='Test', latitude=52, longitude=4)
            self.assertEqual(GameObjectInput(**payload).reward_points, reward)
            self.assertEqual(GameObjectInput(**payload, reward_points=123).reward_points, 123)

    def test_existing_rewards_change_without_rewriting_earned_scores(self):
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            game = Game(name='Ronde-A')
            db.add(game); db.flush()
            team = Team(game_id=game.id, name='Team')
            db.add(team); db.flush()
            entries = []
            for kind, model, extra in (
                (ObjectType.PUZZLE, Puzzle, {'question': '?', 'answer_hash': 'unused', 'reward_points': 100}),
                (ObjectType.PHYSICAL_DUCK, Duck, {'scan_token_hash': 'unused', 'reward_points': 100}),
                (ObjectType.PHOTO_POINT, PhotoPoint, {'reward_points': 100}),
                (ObjectType.CAPTURE_POINT, CapturePoint, {'capture_reward': 100, 'points_per_minute': 5}),
            ):
                obj = GameObject(game_id=game.id, type=kind, name=kind.value, latitude=52, longitude=4, description='je ontvangt 30 volgers bij verovering')
                db.add(obj); db.flush()
                detail = model(game_object_id=obj.id, **extra)
                db.add(detail); entries.append(detail)
            db.add(ScoreEvent(team_id=team.id, type=ScoreType.ADMIN_ADJUSTMENT, reference_id='history', points=123))
            db.commit()
            migration.apply_updates(db); db.commit(); db.expire_all()
            self.assertEqual([row.reward_points for row in entries[:3]], [20, 50, 20])
            self.assertEqual(entries[3].capture_reward, 5)
            self.assertEqual(entries[3].points_per_minute, 5)
            self.assertEqual(db.query(ScoreEvent).one().points, 123)
            self.assertEqual(db.get(GameObject, entries[3].game_object_id).description, 'je ontvangt 5 volgers bij verovering')
        engine.dispose()


if __name__ == '__main__':
    unittest.main()
