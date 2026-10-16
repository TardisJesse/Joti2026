from sqlalchemy.pool import StaticPool
import json
from collections import Counter
from pathlib import Path
from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.board_setup import install_boards, restore_boards, PACK_FILE
from app.game_clock import game_dto
from app.models import Game, GameObject, GameStatus, ScoreEvent, ScoreType, Team, User, BoardInstallation
from app.services import distance_meters

PACK = json.loads((PACK_FILE.parent/'allart_joti_2026_compact_v2.json').read_text(encoding='utf-8'))

def boundary_margin(lat, lng):
    ring = PACK['play_area']['coordinates'][0]; x,y=lng*68500,lat*111195; inside=False; margins=[]
    for a,b in zip(ring,ring[1:]):
        ax,ay=a[0]*68500,a[1]*111195;bx,by=b[0]*68500,b[1]*111195
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
        dx,dy=bx-ax,by-ay;t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
        margins.append(((x-ax-t*dx)**2+(y-ay-t*dy)**2)**.5)
    return min(margins) if inside else -min(margins)

class CompactBoardTests(TestCase):
    def test_approved_coordinates_and_zones(self):
        self.assertEqual(PACK['play_area']['coordinates'][0][-2],[4.330215,51.937997])
        ids=[]
        for board in PACK['boards']:
            self.assertEqual(Counter(o['type'] for o in board['objects']),{'CAPTURE_POINT':8,'PHOTO_POINT':8,'PUZZLE':8,'SCANNER_POINT':2})
            for i,a in enumerate(board['objects']):
                ids.append(a['id']);self.assertNotIn('answer',a);self.assertTrue(a['osm_way_ids'])
                self.assertGreater(boundary_margin(a['latitude'],a['longitude']),a['activation_radius_meters'])
                for b in board['objects'][i+1:]:
                    self.assertGreater(distance_meters(a['latitude'],a['longitude'],b['latitude'],b['longitude']),a['activation_radius_meters']+b['activation_radius_meters'])
            scanner=next(o for o in board['objects'] if o['name'].startswith('S1 '))
            self.assertLess(distance_meters(scanner['latitude'],scanner['longitude'],51.93761748,4.35009742),80)
            self.assertEqual([o['points_per_minute'] for o in board['objects'] if o['type']=='CAPTURE_POINT'],[5]*8)
        self.assertEqual(len(set(ids)),52)
        old=json.loads(PACK_FILE.read_text())
        for obj in old['boards'][0]['objects']:
            self.assertGreater(boundary_margin(obj['latitude'],obj['longitude']),obj['activation_radius_meters'])

    def test_replaces_only_main_boards_preserves_history_and_restores_old_board(self):
        engine=create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool);Base.metadata.create_all(engine)
        with Session(engine) as db:
            install_boards(db);db.commit()
            test=db.query(Game).filter_by(game_code='RONDE-TEST').one();test.status=GameStatus.PAUSED;test.timer_remaining_seconds=17
            game=db.query(Game).filter_by(game_code='RONDE-A').one();old_ids={o.id for o in db.query(GameObject).filter_by(game_id=game.id,active=True)}
            team=Team(game_id=game.id,name='Valken');db.add(team);db.flush()
            db.add(User(team_id=team.id,name='Valken',password_hash='unused',profile_image='portrait'))
            db.add(ScoreEvent(team_id=team.id,type=ScoreType.ADMIN_ADJUSTMENT,reference_id='history',points=42));db.commit()
            result=install_boards(db,PACK);db.commit()
            self.assertEqual([r['objects'] for r in result],[26,26]);self.assertEqual([r['retired'] for r in result],[21,21])
            self.assertEqual(db.query(GameObject).filter_by(active=True).count(),58)
            self.assertEqual(test.status,GameStatus.PAUSED);self.assertEqual(test.timer_remaining_seconds,17)
            self.assertEqual(db.query(ScoreEvent).one().points,42);self.assertEqual(db.query(User).one().profile_image,'portrait')
            self.assertEqual(game_dto(game)['play_area'],PACK['play_area'])
            self.assertTrue(all(r['skipped'] for r in install_boards(db,PACK)))
            restore_boards(db,PACK['version']);db.commit()
            self.assertEqual({o.id for o in db.query(GameObject).filter_by(game_id=game.id,active=True)},old_ids)
            self.assertIsNone(game.play_area_json)
        engine.dispose()
