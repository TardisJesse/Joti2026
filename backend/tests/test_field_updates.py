import importlib.util
from pathlib import Path
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import *
from app.main import game_objects

spec = importlib.util.spec_from_file_location('field_updates', Path(__file__).parents[1] / 'alembic/versions/0012_field_updates.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class FieldUpdatesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        with self.engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.game = Game(name='Ronde-A', game_code='RONDE-A', status=GameStatus.READY)
        self.db.add(self.game); self.db.flush()
        self.team = Team(game_id=self.game.id, name='Team', color='#00ffff')
        self.other = Team(game_id=self.game.id, name='Other', color='#ff0000')
        self.db.add_all([self.team, self.other]); self.db.flush()
        self.player = User(name='Player', team_id=self.team.id, password_hash='unused')
        self.admin = User(name='Admin', role=UserRole.ADMIN, password_hash='unused')
        self.db.add_all([self.player, self.admin]); self.db.flush()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def test_completion_is_per_team_persistent_and_only_for_rewarded_tasks(self):
        for kind, model, score_type, extra in (
            (ObjectType.PUZZLE, Puzzle, ScoreType.PUZZLE_SOLVED, {'question': '?', 'answer_hash': 'unused'}),
            (ObjectType.PHOTO_POINT, PhotoPoint, ScoreType.PHOTO_SUBMITTED, {}),
            (ObjectType.PHYSICAL_DUCK, Duck, ScoreType.DUCK_FOUND, {'scan_token_hash': 'unused'}),
        ):
            obj = GameObject(game_id=self.game.id, type=kind, name=kind.value, latitude=52, longitude=4)
            self.db.add(obj); self.db.flush()
            detail = model(game_object_id=obj.id, reward_points=50, **extra)
            self.db.add(detail); self.db.flush()
            self.db.add(ScoreEvent(team_id=self.team.id, type=score_type, reference_id=detail.id, points=50))
        self.db.commit(); self.db.expire_all()
        self.assertTrue(all(row['completed'] for row in game_objects(None, self.player, self.db)))
        self.player.team_id = self.other.id; self.db.commit()
        self.assertFalse(any(row['completed'] for row in game_objects(None, self.player, self.db)))
        self.assertFalse(any(row['completed'] for row in game_objects(self.game.id, self.admin, self.db)))

    def test_cleanup_with_foreign_keys_keeps_three_rounds_and_their_history(self):
        for code in ('RONDE-B', 'RONDE-TEST', 'GPS-TEST'):
            self.db.add(Game(game_code=code, name=code, status=GameStatus.READY))
        self.db.flush()
        obsolete = self.db.query(Game).filter_by(game_code='GPS-TEST').one()
        team = Team(game_id=obsolete.id, name='Old', color='#ffff00')
        self.db.add(team); self.db.flush()
        player = User(name='Old player', team_id=team.id, password_hash='unused')
        self.admin.team_id = team.id
        self.db.add(player); self.db.flush()
        obj = GameObject(game_id=obsolete.id, type=ObjectType.PHOTO_POINT, name='Old', latitude=52, longitude=4)
        tower = GameObject(game_id=self.game.id, type=ObjectType.CAPTURE_POINT, name='Tower', latitude=52, longitude=4, description='Houd 45 seconden de zone vast.' + migration.WARNING)
        self.db.add_all([obj, tower]); self.db.flush()
        photo = PhotoPoint(game_object_id=obj.id)
        capture = CapturePoint(game_object_id=tower.id, capture_seconds=45)
        self.db.add_all([photo, capture]); self.db.flush()
        self.db.add_all([
            PhotoSubmission(photo_point_id=photo.id, team_id=team.id, user_id=player.id, image='unused'),
            ScoreEvent(team_id=team.id, type=ScoreType.PHOTO_SUBMITTED, reference_id=photo.id, points=50),
            ScoreEvent(team_id=self.team.id, type=ScoreType.ADMIN_ADJUSTMENT, reference_id='keep', points=123),
            PushSubscription(user_id=player.id, endpoint='old', keys_json='{}'),
            NewsEvent(game_id=obsolete.id, kind='TEST', message='test', source_key='old'),
            BoardInstallation(game_id=obsolete.id, version='old', snapshot_json='{}', object_ids_json='[]'),
        ])
        self.db.commit()
        migration.apply_updates(self.db); self.db.commit(); self.db.expire_all()
        self.assertEqual({g.game_code for g in self.db.query(Game)}, {'RONDE-A', 'RONDE-B', 'RONDE-TEST'})
        self.assertEqual(self.db.query(PhotoSubmission).count(), 0)
        self.assertEqual(self.db.query(ScoreEvent).one().points, 123)
        self.assertIsNotNone(self.db.get(User, self.admin.id))
        self.assertIsNone(self.admin.team_id)
        self.assertEqual(capture.capture_seconds, 10)
        self.assertEqual(tower.description, 'Houd 10 seconden de zone vast.')
        migration.apply_updates(self.db); self.db.commit()
        self.assertEqual(self.db.query(Game).count(), 3)


if __name__ == '__main__':
    unittest.main()
