import asyncio
import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch
from PIL import Image
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import *
from app.capture_income import settle_capture_income
from app.main import photos, submit_photo, profile_image, scores, locations, set_game_status, create_game_object
from app.schemas import ImageInput, GameStatusInput, GameObjectInput
from app.services import require_nearby


def image_payload():
    output = BytesIO()
    Image.new('RGB', (20, 20), '#00dff2').save(output, 'PNG')
    return ImageInput(image='data:image/png;base64,' + base64.b64encode(output.getvalue()).decode())


class FeatureTests(TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.game = Game(name='Round', status=GameStatus.RUNNING)
        self.db.add(self.game); self.db.flush()
        self.team = Team(name='Photo Team', game_id=self.game.id)
        self.other = Team(name='Other Team', game_id=self.game.id, color='#ff0000')
        self.db.add_all([self.team, self.other]); self.db.flush()
        self.player = User(name='team-internal-id', team_id=self.team.id, role=UserRole.TEAM_LEADER, password_hash='unused')
        self.admin = User(name='admin', role=UserRole.ADMIN, password_hash='unused')
        self.obj = GameObject(game_id=self.game.id, type=ObjectType.PHOTO_POINT, name='Team photo', latitude=51.9, longitude=4.3)
        self.capture_obj = GameObject(game_id=self.game.id, type=ObjectType.CAPTURE_POINT, name='Tower', latitude=51.9, longitude=4.3)
        self.db.add_all([self.player, self.admin, self.obj, self.capture_obj]); self.db.flush()
        self.photo_point = PhotoPoint(game_object_id=self.obj.id, reward_points=10)
        self.at = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        self.point = CapturePoint(game_object_id=self.capture_obj.id, owner_team_id=self.team.id, income_updated_at=self.at, points_per_minute=1)
        self.db.add_all([self.photo_point, self.point]); self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def income(self, seconds):
        settle_capture_income(self.db, self.game.id, self.at + timedelta(seconds=seconds)); self.db.commit()

    def total(self, team):
        return sum(row.points for row in self.db.query(ScoreEvent).filter_by(team_id=team.id))

    def test_income_full_minutes_and_repeated_reads(self):
        self.income(59); self.assertEqual(self.total(self.team), 0)
        self.income(60); self.assertEqual(self.total(self.team), 1)
        self.income(60); self.assertEqual(self.total(self.team), 1)
        self.income(185); self.assertEqual(self.total(self.team), 3)
        # A new session after a restart catches up from the persisted clock.
        game_id, team_id = self.game.id, self.team.id
        self.db.close(); self.db = Session(self.engine)
        self.game = self.db.get(Game, game_id); self.team = self.db.get(Team, team_id)
        self.income(300); self.assertEqual(self.total(self.team), 5)

    def test_pause_keeps_partial_minute_and_stops_income(self):
        self.income(30)
        self.game.status = GameStatus.PAUSED; self.db.commit()
        self.income(330); self.assertEqual(self.total(self.team), 0)
        self.game.status = GameStatus.RUNNING; self.db.commit()
        self.income(360); self.assertEqual(self.total(self.team), 1)
        self.capture_obj.active = False; self.db.commit()
        self.income(480); self.assertEqual(self.total(self.team), 1)

    def test_owner_transfer_settles_old_owner_and_resets_partial(self):
        self.income(90)
        self.point.owner_team_id = self.other.id
        self.point.income_remainder_seconds = 0
        self.db.commit()
        self.income(149); self.assertEqual(self.total(self.other), 0)
        self.income(150); self.assertEqual(self.total(self.other), 1)
        self.assertEqual(self.total(self.team), 1)

    def test_status_transition_settles_before_pause(self):
        with patch('app.capture_income.datetime') as clock:
            clock.now.return_value = self.at + timedelta(seconds=90)
            set_game_status(self.game.id, GameStatusInput(status='PAUSED'), self.admin, self.db)
        self.assertEqual(self.total(self.team), 1)
        self.income(500); self.assertEqual(self.total(self.team), 1)

    def test_profile_image_persisted_and_exposed_in_rankings_and_locations(self):
        result = asyncio.run(profile_image(image_payload(), self.player, self.db))
        self.assertTrue(result['profile_image'].startswith('data:image/jpeg;base64,'))
        self.game.status = GameStatus.PAUSED; self.db.commit()
        rows = scores(None, self.player, self.db)
        self.assertEqual(next(r for r in rows if r['team_id'] == self.team.id)['profile_image'], result['profile_image'])
        with patch('app.main.get_location', return_value={'lat': 51.9, 'lng': 4.3}):
            players = locations(self.game.id, self.admin, self.db)
        self.assertEqual(players[0]['team_name'], 'Photo Team')
        self.assertEqual(players[0]['profile_image'], result['profile_image'])
        with self.assertRaises(HTTPException):
            asyncio.run(profile_image(ImageInput(image='data:image/svg+xml;base64,abc'), self.player, self.db))

    def test_photo_submit_gallery_and_duplicate_reward(self):
        with patch('app.main.require_nearby'):
            result = asyncio.run(submit_photo(self.obj.id, image_payload(), self.player, self.db))
            self.assertEqual(result['points'], 10)
            gallery = photos(self.obj.id, self.player, self.db)
            self.assertTrue(gallery['submitted']); self.assertEqual(gallery['photos'][0]['team_name'], 'Photo Team')
            with self.assertRaises(HTTPException) as duplicate:
                asyncio.run(submit_photo(self.obj.id, image_payload(), self.player, self.db))
            self.assertEqual(duplicate.exception.status_code, 409)
        self.assertEqual(self.total(self.team), 10)

    def test_photo_requires_range_and_same_round(self):
        with patch('app.main.require_nearby', side_effect=HTTPException(403, 'Out of range')):
            for call in [lambda: photos(self.obj.id, self.player, self.db), lambda: asyncio.run(submit_photo(self.obj.id, image_payload(), self.player, self.db))]:
                with self.assertRaises(HTTPException): call()
        self.assertEqual(self.db.query(PhotoSubmission).count(), 0)
        another_game = Game(name='Other', status=GameStatus.RUNNING)
        self.db.add(another_game); self.db.flush()
        self.obj.game_id = another_game.id; self.db.commit()
        with self.assertRaises(HTTPException) as wrong_round:
            photos(self.obj.id, self.player, self.db)
        self.assertEqual(wrong_round.exception.status_code, 404)

    def test_admin_creates_photo_point(self):
        payload = GameObjectInput(game_id=self.game.id, type='PHOTO_POINT', name='Camera', latitude=51.9, longitude=4.3, reward_points=25)
        result = asyncio.run(create_game_object(payload, self.admin, self.db))
        self.assertEqual(self.db.query(PhotoPoint).filter_by(game_object_id=result['id']).one().reward_points, 25)
        self.assertNotIn('scan_token', result)

    def test_stale_gps_rejected(self):
        loc = {'lat': 51.9, 'lng': 4.3, 'accuracy': 10, 'updated_at': (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}
        with patch('app.services.get_location', return_value=loc):
            with self.assertRaises(HTTPException) as stale:
                require_nearby(self.player.id, 51.9, 4.3, 40)
        self.assertEqual(stale.exception.status_code, 409)
