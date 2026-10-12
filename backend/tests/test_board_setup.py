import json
from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import *
from app.board_setup import PACK_FILE, install_boards, restore_boards
from app.services import distance_meters


class BoardSetupTests(TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db=Session(self.engine)
        self.pack=json.loads(PACK_FILE.read_text(encoding='utf-8'))

    def tearDown(self):
        self.db.close();self.engine.dispose()

    def test_fresh_install_has_three_complete_ready_rounds(self):
        result=install_boards(self.db);self.db.commit()
        self.assertEqual([row['objects'] for row in result],[6,21,21])
        self.assertEqual(self.db.query(GameObject).filter_by(active=True).count(),48)
        self.assertEqual(self.db.query(Puzzle).count(),18)
        self.assertEqual(self.db.query(PhotoPoint).count(),14)
        self.assertEqual(self.db.query(CapturePoint).count(),11)
        self.assertEqual(self.db.query(GameObject).filter_by(type=ObjectType.SCANNER_POINT).count(),5)
        self.assertTrue(all(game.status==GameStatus.READY and game.ends_at is None for game in self.db.query(Game)))
        self.assertEqual(self.db.query(NewsEvent).count(),3)

    def test_normalized_existing_round_preserves_players_scores_and_undo_snapshot(self):
        game=Game(game_code='RONDE_A',name='Existing A',status=GameStatus.PAUSED,timer_remaining_seconds=37)
        untouched=Game(game_code='OTHER',name='Other',status=GameStatus.READY)
        self.db.add_all([game,untouched]);self.db.flush()
        team=Team(game_id=game.id,name='Valken');self.db.add(team);self.db.flush()
        user=User(team_id=team.id,name='existing',password_hash='unused',profile_image='saved-photo')
        old=GameObject(game_id=game.id,type=ObjectType.CAPTURE_POINT,name='Old',latitude=52,longitude=4)
        other=GameObject(game_id=untouched.id,type=ObjectType.SCANNER_POINT,name='Untouched',latitude=52,longitude=4)
        self.db.add_all([user,old,other]);self.db.flush()
        self.db.add(CapturePoint(game_object_id=old.id,owner_team_id=team.id))
        self.db.add(ScoreEvent(team_id=team.id,type=ScoreType.ADMIN_ADJUSTMENT,reference_id='history',points=42));self.db.commit()
        install_boards(self.db);self.db.commit()
        self.assertEqual(self.db.query(Game).count(),4)
        self.assertEqual(game.game_code,'RONDE_A');self.assertEqual(game.name,'Ronde A')
        self.assertFalse(old.active);self.assertTrue(other.active)
        self.assertEqual(user.profile_image,'saved-photo')
        self.assertEqual(self.db.query(ScoreEvent).one().points,42)
        restore_boards(self.db,self.pack['version']);self.db.commit()
        self.assertTrue(old.active);self.assertTrue(other.active)
        self.assertEqual(game.name,'Existing A');self.assertEqual(game.status,GameStatus.PAUSED)
        self.assertEqual(game.timer_remaining_seconds,37)
        self.assertEqual(self.db.query(GameObject).filter_by(game_id=game.id,active=True).count(),1)

    def test_name_matching_works_when_existing_code_is_different(self):
        game=Game(game_code='MY-TEST',name='Ronde-Test',status=GameStatus.READY)
        self.db.add(game);self.db.commit()
        install_boards(self.db);self.db.commit()
        self.assertEqual(self.db.query(Game).count(),3)
        self.assertEqual(game.game_code,'MY-TEST')
        self.assertEqual(self.db.query(GameObject).filter_by(game_id=game.id,active=True).count(),6)

    def test_repeat_does_not_reset_admin_changes_or_create_duplicates(self):
        install_boards(self.db);self.db.commit()
        obj=self.db.query(GameObject).filter_by(type=ObjectType.CAPTURE_POINT).first();obj.active=False
        game=self.db.get(Game,obj.game_id);game.status=GameStatus.RUNNING;self.db.commit()
        rows=install_boards(self.db);self.db.commit()
        self.assertTrue(all(row['skipped'] for row in rows))
        self.assertFalse(obj.active);self.assertEqual(game.status,GameStatus.RUNNING)
        self.assertEqual(self.db.query(GameObject).count(),48)
        self.assertEqual(self.db.query(NewsEvent).count(),3)

    def test_ambiguous_rounds_abort_instead_of_overwriting(self):
        self.db.add_all([Game(game_code='RONDE-A',name='One'),Game(game_code='RONDE_A',name='Two')]);self.db.commit()
        with self.assertRaises(ValueError):install_boards(self.db)
        self.db.rollback()
        self.assertEqual(self.db.query(Game).count(),2)
        self.assertEqual(self.db.query(GameObject).count(),0)

    def test_pack_has_nonoverlapping_zones_within_two_kilometres_and_real_path_sources(self):
        hq=self.pack['hq'];ids=[]
        for board in self.pack['boards']:
            self.assertLess(board['walking_loop_m'],4500)
            for point in board['objects']:
                ids.append(point['id']);self.assertTrue(point['osm_way_ids'])
                self.assertLess(distance_meters(hq['latitude'],hq['longitude'],point['latitude'],point['longitude']),2000)
                self.assertNotIn('answer',point)
                if point['type']=='PUZZLE':self.assertTrue(point['answer_hash'].startswith('$argon2'))
            for i,a in enumerate(board['objects']):
                for b in board['objects'][i+1:]:
                    self.assertGreater(distance_meters(a['latitude'],a['longitude'],b['latitude'],b['longitude']),a['activation_radius_meters']+b['activation_radius_meters'])
        self.assertEqual(len(set(ids)),48)
