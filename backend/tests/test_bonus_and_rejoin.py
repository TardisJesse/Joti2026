from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Game, GameStatus, Team, User, UserRole, GameObject, ObjectType, CapturePoint, ScoreEvent, ScoreType
from app.bonus import bonus_state
from app.capture_income import settle_capture_income
from app.main import join_game
from app.schemas import GameJoinInput


class BonusAndRejoinTests(TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.at = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        self.game = Game(name='Round', game_code='ROUND-A', status=GameStatus.RUNNING, bonus_updated_at=self.at)
        self.db.add(self.game); self.db.flush()
        self.team = Team(name='Valken', game_id=self.game.id)
        self.db.add(self.team); self.db.flush()
        self.player = User(name='team-player', team_id=self.team.id, role=UserRole.TEAM_LEADER, password_hash='unused', profile_image='saved-photo')
        self.db.add(self.player)
        self.ids = ['a', 'b']
        for object_id in self.ids:
            obj = GameObject(id=object_id, game_id=self.game.id, type=ObjectType.CAPTURE_POINT, name=object_id, latitude=52, longitude=4)
            self.db.add(obj); self.db.flush()
            self.db.add(CapturePoint(game_object_id=obj.id, owner_team_id=self.team.id, income_updated_at=self.at, points_per_minute=1))
        self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def income(self, seconds):
        settle_capture_income(self.db, self.game.id, self.at + timedelta(seconds=seconds)); self.db.commit()

    def total(self):
        return sum(row.points for row in self.db.query(ScoreEvent).all())

    def test_rotation_and_exact_boundaries(self):
        self.assertIsNone(bonus_state(self.game, self.ids, self.at + timedelta(seconds=599)))
        self.assertEqual(bonus_state(self.game, self.ids, self.at + timedelta(seconds=600))['object_id'], 'a')
        self.assertIsNone(bonus_state(self.game, self.ids, self.at + timedelta(seconds=900)))
        self.assertEqual(bonus_state(self.game, self.ids, self.at + timedelta(seconds=1200))['object_id'], 'b')
        self.assertEqual(bonus_state(self.game, self.ids, self.at + timedelta(seconds=1800))['object_id'], 'a')
        self.assertIsNone(bonus_state(self.game, [], self.at + timedelta(seconds=600)))

    def test_delayed_settlement_crosses_multiple_bonuses_without_duplicates(self):
        self.income(1500)
        self.assertEqual(self.total(), 60)  # 25 normal minutes per post + five bonus minutes each.
        self.income(1500); self.assertEqual(self.total(), 60)
        self.db.expire_all()
        self.income(1800); self.assertEqual(self.total(), 70)

    def test_polling_frequency_does_not_change_rewards(self):
        for seconds in range(15, 1501, 15):
            self.income(seconds)
        self.assertEqual(self.total(), 60)

    def test_pause_freezes_rotation_and_income(self):
        self.income(650)
        self.game.status = GameStatus.PAUSED; self.db.commit()
        self.income(1250)
        self.assertEqual(self.game.bonus_elapsed_seconds, 650)
        self.assertIsNone(bonus_state(self.game, self.ids, self.at + timedelta(seconds=1250)))
        self.game.status = GameStatus.RUNNING; self.db.commit()
        self.assertEqual(bonus_state(self.game, self.ids, self.at + timedelta(seconds=1260))['object_id'], 'a')
        self.income(1500)
        self.assertEqual(self.game.bonus_elapsed_seconds, 900)
        self.assertEqual(self.total(), 35)

    def test_deadline_stops_bonus_income(self):
        self.game.ends_at = self.at + timedelta(seconds=900); self.db.commit()
        self.income(1500)
        self.assertEqual(self.total(), 35)
        self.assertIsNone(bonus_state(self.game, self.ids, self.at + timedelta(seconds=1500)))

    def test_rejoin_preserves_account_score_and_photo_even_after_finish(self):
        self.game.status = GameStatus.FINISHED
        self.db.add(ScoreEvent(team_id=self.team.id, type=ScoreType.ADMIN_ADJUSTMENT, points=42, reference_id='score'))
        self.db.commit()
        result = join_game(GameJoinInput(game_code='round-a', team_name=' valKEN '), self.db)
        self.assertEqual(result['user']['id'], self.player.id)
        self.assertEqual(result['user']['profile_image'], 'saved-photo')
        self.assertEqual(result['user']['team_id'], self.team.id)
        self.assertTrue(result['access_token'])
        self.assertEqual(self.total(), 42)
        self.assertEqual(self.db.query(Team).count(), 1)
        self.assertEqual(self.db.query(User).count(), 1)
        with self.assertRaises(HTTPException):
            join_game(GameJoinInput(game_code='ROUND-A', team_name='New team'), self.db)

    def test_same_name_other_round_is_a_new_team_and_inactive_account_cannot_rejoin(self):
        other = Game(name='Other', game_code='ROUND-B', status=GameStatus.READY)
        self.db.add(other); self.db.commit()
        with patch('app.main.hash_password', return_value='unused'):
            result = join_game(GameJoinInput(game_code='ROUND-B', team_name='Valken'), self.db)
        self.assertNotEqual(result['user']['team_id'], self.team.id)
        self.player.active = False; self.db.commit()
        with self.assertRaises(HTTPException) as raised:
            join_game(GameJoinInput(game_code='ROUND-A', team_name='Valken'), self.db)
        self.assertEqual(raised.exception.status_code, 403)
