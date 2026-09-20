import asyncio
import time
import unittest
from unittest.mock import patch
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Game, GameStatus, Team, User, UserRole, GameObject, ObjectType, CapturePoint
from app.main import game_objects, capture_status, delete_game_object
from app.services import capture_started, subscribers, cooldowns
from app.team_colors import next_team_color
from app.security import require_admin


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.game = Game(name='Round', status=GameStatus.RUNNING)
        self.db.add(self.game); self.db.flush()
        self.team = Team(name='Cyan', game_id=self.game.id, color='#00dff2')
        self.db.add(self.team); self.db.flush()
        self.player = User(name='Player', role=UserRole.TEAM_LEADER, password_hash='unused', team_id=self.team.id)
        self.point = GameObject(name='Flag', game_id=self.game.id, type=ObjectType.CAPTURE_POINT, latitude=51.9, longitude=4.3, activation_radius_meters=40)
        self.db.add_all([self.player, self.point]); self.db.flush()
        self.capture = CapturePoint(game_object_id=self.point.id, capture_seconds=5, cooldown_seconds=30, capture_reward=20)
        self.db.add(self.capture); self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose(); capture_started.clear(); cooldowns.clear(); subscribers.clear()

    def test_unique_colors(self):
        colors = set()
        for _ in range(100): colors.add(next_team_color(colors))
        self.assertEqual(len(colors), 100)

    def test_capture_owner_event_and_push_scope(self):
        queue = asyncio.Queue(); unrelated = asyncio.Queue()
        subscribers[f'game:{self.game.id}:events'].add(queue)
        subscribers['game:other:events'].add(unrelated)
        capture_started[(self.capture.id, self.team.id)] = time.monotonic() - 6
        tasks = BackgroundTasks()
        with patch('app.main.require_nearby'):
            result = asyncio.run(capture_status(self.point.id, tasks, self.player, self.db))
        self.assertEqual(result['state'], 'COMPLETED')
        event = queue.get_nowait()
        self.assertEqual(event['data']['owner_team_name'], 'Cyan')
        self.assertTrue(unrelated.empty())
        self.assertEqual(tasks.tasks[0].args[0], self.game.id)
        rows = game_objects(None, self.player, self.db)
        self.assertEqual(rows[0]['owner_team_color'], '#00dff2')
        with patch('app.main.require_nearby'):
            self.assertEqual(asyncio.run(capture_status(self.point.id, BackgroundTasks(), self.player, self.db))['state'], 'IDLE')

    def test_soft_delete_scope(self):
        with self.assertRaises(HTTPException) as denied:
            require_admin(self.player)
        self.assertEqual(denied.exception.status_code, 403)
        admin = User(name='Admin', role=UserRole.ADMIN, password_hash='unused')
        self.db.add(admin); self.db.commit()
        with self.assertRaises(HTTPException):
            asyncio.run(delete_game_object(self.point.id, 'other', admin, self.db))
        asyncio.run(delete_game_object(self.point.id, self.game.id, admin, self.db))
        self.assertEqual(game_objects(None, self.player, self.db), [])
        self.assertIsNotNone(self.db.get(GameObject, self.point.id))

    def test_push_targets_only_same_round(self):
        import json
        from app.models import PushSubscription
        from app.push import notify_capture
        other_game = Game(name='Other', status=GameStatus.RUNNING)
        self.db.add(other_game); self.db.flush()
        other_team = Team(name='Other', game_id=other_game.id, color='#00dff2')
        self.db.add(other_team); self.db.flush()
        other_user = User(name='Other', role=UserRole.PLAYER, password_hash='unused', team_id=other_team.id)
        self.db.add(other_user); self.db.flush()
        self.db.add_all([PushSubscription(user_id=self.player.id, endpoint='https://fcm.googleapis.com/own', keys_json=json.dumps({'p256dh': 'key', 'auth': 'key'})), PushSubscription(user_id=other_user.id, endpoint='https://fcm.googleapis.com/other', keys_json='{}')]); self.db.commit()
        with patch('app.push.SessionLocal', return_value=self.db), patch('app.push.enabled', return_value=True), patch.dict('os.environ', {'VAPID_PRIVATE_KEY': 'test', 'VAPID_SUBJECT': 'mailto:test@example.com'}), patch('app.push.webpush') as send:
            notify_capture(self.game.id, 'Flag', 'Cyan')
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.kwargs['subscription_info']['endpoint'], 'https://fcm.googleapis.com/own')


if __name__ == '__main__': unittest.main()
