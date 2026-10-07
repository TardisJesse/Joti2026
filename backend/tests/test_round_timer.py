import asyncio
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.database import Base
import test_photos_and_income as fixtures
from app.models import Game, GameStatus, GameObject, ObjectType, ScoreEvent, Duck
from app.main import set_round_timer, remove_round_timer, set_game_status, current_game, object_for, submit_photo
from app.main import start_round_clock, stop_round_clock
from app.main import answer, duck_scan
from app.game_clock import expire_game, expire_due_games
from app.capture_income import utc
from app.schemas import GameTimerInput, GameStatusInput, AnswerInput, ScanInput
from app.security import require_admin
from app.services import capture_started, subscribers
from app.services import hash_token


class TimerTests(TestCase):
    def setUp(self):
        fixtures.FeatureTests.setUp(self)
        self.at = datetime.now(timezone.utc)
        self.point.income_updated_at = self.at
        self.db.commit()

    def tearDown(self):
        fixtures.FeatureTests.tearDown(self)
        capture_started.clear(); subscribers.clear()

    def start(self, seconds=60):
        with patch('app.capture_income.datetime') as clock:
            clock.now.return_value = self.at
            return asyncio.run(set_round_timer(self.game.id, GameTimerInput(duration_seconds=seconds), self.admin, self.db))

    def test_timer_start_and_public_state(self):
        queue = asyncio.Queue()
        subscribers[f'game:{self.game.id}:events'].add(queue)
        self.game.status = GameStatus.READY; self.db.commit()
        result = self.start(120)
        self.assertEqual(result['status'], GameStatus.RUNNING)
        self.assertEqual(datetime.fromisoformat(result['ends_at']), self.at + timedelta(seconds=120))
        self.assertEqual(queue.get_nowait()['type'], 'GAME_UPDATED')
        public = current_game(None, self.player, self.db)
        self.assertEqual(public['ends_at'], result['ends_at'])
        self.assertIn('server_now', public)

    def test_only_admin_can_set_timer_and_duration_is_bounded(self):
        with self.assertRaises(HTTPException) as denied:
            require_admin(self.player)
        self.assertEqual(denied.exception.status_code, 403)
        for seconds in (0, 59, 86401):
            with self.assertRaises(ValidationError): GameTimerInput(duration_seconds=seconds)
        self.assertEqual(GameTimerInput(duration_seconds=86400).duration_seconds, 86400)

    def test_expiry_stops_at_exact_deadline_and_caps_income(self):
        self.start()
        capture_started[(self.point.id, self.team.id)] = 10
        self.assertFalse(expire_game(self.db, self.game, self.at + timedelta(seconds=59)))
        self.assertTrue(expire_game(self.db, self.game, self.at + timedelta(seconds=180)))
        self.db.commit()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(sum(event.points for event in self.db.query(ScoreEvent)), 1)
        self.assertNotIn((self.point.id, self.team.id), capture_started)
        self.assertFalse(expire_game(self.db, self.game, self.at + timedelta(seconds=500)))
        for obj, kind in [(self.obj, ObjectType.PHOTO_POINT), (self.capture_obj, ObjectType.CAPTURE_POINT)]:
            with self.assertRaises(HTTPException) as stopped:
                object_for(obj.id, kind, self.player, self.db)
            self.assertEqual(stopped.exception.status_code, 409)
        with self.assertRaises(HTTPException):
            asyncio.run(submit_photo(self.obj.id, fixtures.image_payload(), self.player, self.db))
        puzzle = GameObject(game_id=self.game.id, type=ObjectType.PUZZLE, name='Puzzle', latitude=51.9, longitude=4.3)
        duck_obj = GameObject(game_id=self.game.id, type=ObjectType.PHYSICAL_DUCK, name='Duck', latitude=51.9, longitude=4.3)
        self.db.add_all([puzzle, duck_obj]); self.db.flush()
        token = 'timer-test-duck-token'
        self.db.add(Duck(game_object_id=duck_obj.id, scan_token_hash=hash_token(token)))
        self.db.commit()
        for action in [lambda: answer(puzzle.id, AnswerInput(answer='test'), self.player, self.db), lambda: duck_scan(ScanInput(token=token), self.player, self.db)]:
            with self.assertRaises(HTTPException) as stopped:
                asyncio.run(action())
            self.assertEqual(stopped.exception.status_code, 409)
        self.assertEqual(self.db.query(ScoreEvent).count(), 1)

    def test_exact_zero_expires(self):
        self.start()
        self.assertTrue(expire_game(self.db, self.game, self.at + timedelta(seconds=60)))

    def test_restart_worker_expires_without_players(self):
        self.start()
        finished = expire_due_games(sessionmaker(bind=self.engine), self.at + timedelta(seconds=70))
        self.db.expire_all()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(finished[0]['id'], self.game.id)
        self.assertEqual(expire_due_games(sessionmaker(bind=self.engine), self.at + timedelta(seconds=80)), [])

    def test_pause_resume_preserves_time(self):
        self.start(120)
        with patch('app.capture_income.datetime') as clock:
            clock.now.return_value = self.at + timedelta(seconds=30)
            set_game_status(self.game.id, GameStatusInput(status='PAUSED'), self.admin, self.db)
        self.assertIsNone(self.game.ends_at)
        self.assertEqual(self.game.timer_remaining_seconds, 90)
        self.assertFalse(expire_game(self.db, self.game, self.at + timedelta(seconds=500)))
        with patch('app.capture_income.datetime') as clock:
            clock.now.return_value = self.at + timedelta(seconds=500)
            set_game_status(self.game.id, GameStatusInput(status='RUNNING'), self.admin, self.db)
        self.assertEqual(utc(self.game.ends_at), self.at + timedelta(seconds=590))
        self.assertIsNone(self.game.timer_remaining_seconds)

    def test_remove_and_reset_timer(self):
        self.start(120)
        self.start(60)
        self.assertEqual(utc(self.game.ends_at), self.at + timedelta(seconds=60))
        asyncio.run(remove_round_timer(self.game.id, self.admin, self.db))
        self.assertIsNone(self.game.ends_at)
        self.assertEqual(self.game.status, GameStatus.RUNNING)

    def test_actual_background_loop_finishes_without_requests(self):
        with TemporaryDirectory() as directory:
            engine = create_engine('sqlite:///' + (Path(directory) / 'clock.db').as_posix())
            Base.metadata.create_all(engine)
            factory = sessionmaker(bind=engine)
            with factory() as db:
                game = Game(name='Background round', status=GameStatus.RUNNING, ends_at=datetime.now(timezone.utc) + timedelta(seconds=1))
                db.add(game); db.commit(); game_id = game.id
            async def run():
                queue = asyncio.Queue()
                subscribers[f'game:{game_id}:events'].add(queue)
                with patch('app.main.SessionLocal', factory):
                    await start_round_clock()
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=5)
                        self.assertEqual(event['data']['status'], GameStatus.FINISHED)
                    finally:
                        await stop_round_clock()
            asyncio.run(run())
            with factory() as db:
                self.assertEqual(db.get(Game, game_id).status, GameStatus.FINISHED)
            engine.dispose()
