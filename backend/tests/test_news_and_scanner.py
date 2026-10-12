import asyncio
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.database import Base
from app.models import *
from app.main import scanner_locations, round_news, create_game_object, game_objects, set_game_status
from app.schemas import GameObjectInput, GameStatusInput
from app.news import add_news, collect_news
from app.services import memory_locations, set_location
from app.game_clock import expire_due_games


class NewsScannerTests(TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.game = Game(name='A', status=GameStatus.RUNNING)
        self.other_game = Game(name='B', status=GameStatus.RUNNING)
        self.db.add_all([self.game,self.other_game]); self.db.flush()
        self.teams = [Team(name=f'Team {i}',game_id=self.game.id if i<2 else self.other_game.id,color=f'#00000{i}') for i in range(3)]
        self.db.add_all(self.teams); self.db.flush()
        self.players = [User(name=f'user{i}',team_id=team.id,password_hash='unused',profile_image='photo') for i,team in enumerate(self.teams)]
        self.admin = User(name='admin',role=UserRole.ADMIN,password_hash='unused')
        self.obj = GameObject(game_id=self.game.id,type=ObjectType.SCANNER_POINT,name='Radar',latitude=52,longitude=4)
        self.db.add_all([*self.players,self.admin,self.obj]); self.db.commit()
        self.player=self.players[0]
        self.at=datetime.now(timezone.utc)
        memory_locations.clear()

    def tearDown(self):
        memory_locations.clear();self.db.close();self.engine.dispose()

    def location(self,player,lat=52,age=0,accuracy=10):
        memory_locations[player.id]={'lat':lat,'lng':4,'accuracy':accuracy,'updated_at':(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()}

    def test_scanner_scope_profile_and_no_reward_or_news(self):
        for player in self.players:self.location(player)
        with patch('app.services.redis_client',None):
            result=scanner_locations(self.obj.id,self.player,self.db)
        self.assertEqual(len(result['locations']),1)
        self.assertEqual(result['locations'][0]['team_name'],'Team 1')
        self.assertEqual(result['locations'][0]['profile_image'],'photo')
        self.assertEqual(self.db.query(ScoreEvent).count(),0)
        self.assertEqual(self.db.query(NewsEvent).count(),0)
        with self.assertRaises(HTTPException):scanner_locations(self.obj.id,self.players[2],self.db)

    def test_scanner_range_accuracy_age_pause_finish_and_deletion(self):
        with patch('app.services.redis_client',None):
            for lat,age,accuracy in [(53,0,10),(52,181,10),(52,0,100)]:
                self.location(self.player,lat,age,accuracy)
                with self.assertRaises(HTTPException):scanner_locations(self.obj.id,self.player,self.db)
            self.location(self.player)
            for status in [GameStatus.PAUSED,GameStatus.FINISHED]:
                self.game.status=status;self.db.commit()
                with self.assertRaises(HTTPException):scanner_locations(self.obj.id,self.player,self.db)
            self.game.status=GameStatus.RUNNING;self.obj.active=False;self.db.commit()
            with self.assertRaises(HTTPException):scanner_locations(self.obj.id,self.player,self.db)

    def test_expired_and_inaccurate_targets_are_hidden(self):
        self.location(self.player)
        with patch('app.services.redis_client',None):
            for age,accuracy in [(181,10),(0,80),(-10,10)]:
                self.location(self.players[1],age=age,accuracy=accuracy)
                self.assertEqual(scanner_locations(self.obj.id,self.player,self.db)['locations'],[])

    def test_news_is_scoped_ordered_limited_and_idempotent(self):
        for i in range(55):add_news(self.db,self.game.id,'CAPTURE_COMPLETED',f'event{i}',team_name='Team 1',source_key=f'event{i}',at=self.at+timedelta(seconds=i))
        add_news(self.db,self.other_game.id,'GAME_STATUS','other')
        add_news(self.db,self.game.id,'CAPTURE_COMPLETED','duplicate',source_key='event54')
        self.db.commit()
        rows=round_news(self.other_game.id,self.player,self.db) # Players cannot switch scope.
        self.assertEqual(len(rows),50);self.assertEqual(rows[0]['message'],'event54')
        self.assertEqual(rows[-1]['message'],'event5')
        factory=sessionmaker(self.engine)
        self.assertEqual(len(collect_news(factory)),56)
        self.assertEqual(collect_news(factory),[])

    def test_admin_scanner_creation_and_reward_metadata(self):
        payload=GameObjectInput(game_id=self.game.id,type='SCANNER_POINT',name='New radar',latitude=52,longitude=4)
        result=asyncio.run(create_game_object(payload,self.admin,self.db))
        self.assertNotIn('scan_token',result)
        self.assertEqual(self.db.query(Duck).count(),0)
        obj=GameObject(game_id=self.game.id,type=ObjectType.PUZZLE,name='Puzzle',latitude=52,longitude=4)
        self.db.add(obj);self.db.flush();self.db.add(Puzzle(game_object_id=obj.id,question='?',answer_hash='unused',reward_points=73));self.db.commit()
        rows=game_objects(None,self.player,self.db)
        self.assertEqual(next(row for row in rows if row['id']==obj.id)['reward_points'],73)
        self.assertIsNone(next(row for row in rows if row['id']==self.obj.id)['reward_points'])

    def test_status_and_bonus_news_once(self):
        set_game_status(self.game.id,GameStatusInput(status='PAUSED'),self.admin,self.db)
        set_game_status(self.game.id,GameStatusInput(status='PAUSED'),self.admin,self.db)
        self.assertEqual(self.db.query(NewsEvent).count(),1)
        set_game_status(self.game.id,GameStatusInput(status='RUNNING'),self.admin,self.db)
        tower=GameObject(game_id=self.game.id,type=ObjectType.CAPTURE_POINT,name='North',latitude=52,longitude=4)
        self.db.add(tower);self.db.flush();self.db.add(CapturePoint(game_object_id=tower.id))
        self.game.bonus_elapsed_seconds=601;self.game.bonus_updated_at=datetime.now(timezone.utc);self.db.commit()
        factory=sessionmaker(self.engine)
        collect_news(factory);collect_news(factory)
        self.assertEqual(self.db.query(NewsEvent).filter_by(kind='BONUS_STARTED').count(),1)

    def test_automatic_finish_is_persisted_only_once(self):
        self.game.ends_at=self.at-timedelta(seconds=1);self.db.commit()
        factory=sessionmaker(self.engine)
        self.assertEqual(len(expire_due_games(factory,self.at)),1)
        self.assertEqual(expire_due_games(factory,self.at),[])
        rows=round_news(None,self.player,self.db)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['kind'],'GAME_FINISHED')
