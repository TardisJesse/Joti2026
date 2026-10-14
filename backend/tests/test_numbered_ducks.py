import asyncio
import heapq
import json
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch
from pathlib import Path
from fastapi import HTTPException
from pydantic import ValidationError
from app.board_setup import install_boards, restore_boards, PACK_FILE
from app.main import duck_scan, available_ducks, create_game_object, move_duck, load_locations
from app.models import Duck, DuckScan, Game, GameObject, GameStatus, ObjectType, ScoreEvent, Team, User, UserRole
from app.schemas import ScanInput, GameObjectInput, DuckLocationInput, LoadLocationsInput
from app.services import hash_token, memory_locations
import test_photos_and_income as fixtures

PACK = json.loads((PACK_FILE.parent/'allart_joti_2026_walkable_v3.json').read_text(encoding='utf-8'))

class NumberedDuckTests(TestCase):
    def setUp(self):
        self.redis_patch = patch('app.services.redis_client',None);self.redis_patch.start()
        fixtures.FeatureTests.setUp(self)
        self.obj = GameObject(game_id=self.game.id,type=ObjectType.PHYSICAL_DUCK,name='Eend 3',latitude=51.9,longitude=4.3,activation_radius_meters=20)
        self.db.add(self.obj);self.db.flush()
        self.duck = Duck(game_object_id=self.obj.id,duck_number=3,nfc_serial_hash=hash_token('0481641c460289'),scan_token_hash=hash_token('legacy-test-token'),reward_points=50,search_radius_meters=20)
        self.db.add(self.duck);self.db.commit()
        self.locate()

    def locate(self, **changes):
        memory_locations[self.player.id] = {'lat':51.9,'lng':4.3,'accuracy':5,'updated_at':datetime.now(timezone.utc).isoformat(),**changes}

    def tearDown(self):
        memory_locations.clear();self.redis_patch.stop();fixtures.FeatureTests.tearDown(self)

    def claim(self, **identifier):
        return asyncio.run(duck_scan(ScanInput(**identifier),self.player,self.db))

    def denied(self, status, **identifier):
        with self.assertRaises(HTTPException) as result: self.claim(**identifier)
        self.assertEqual(result.exception.status_code,status)

    def test_nfc_and_number_share_one_reward(self):
        self.assertEqual(self.claim(serial_number='04:81:64:1C:46:02:89')['points'],50)
        self.denied(409,duck_number=3)
        self.denied(409,token='legacy-test-token')
        self.assertEqual(self.db.query(DuckScan).count(),1)
        self.assertEqual(self.db.query(ScoreEvent).one().points,50)

    def test_number_awards_same_reward_and_each_team_can_find_duck(self):
        self.assertEqual(self.claim(duck_number=3)['points'],50)
        self.denied(409,serial_number='0481641c460289')
        self.player.team_id=self.other.id;self.db.commit()
        self.assertEqual(self.claim(duck_number=3)['points'],50)

    def test_distance_accuracy_stale_gps_pause_and_retired_duck_block_both_methods(self):
        for identity in ({'duck_number':3},{'serial_number':'0481641c460289'}):
            self.locate(lat=52);self.denied(403,**identity)
            self.locate(accuracy=100);self.denied(409,**identity)
            self.locate(updated_at=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat());self.denied(409,**identity)
            self.locate();self.game.status=GameStatus.PAUSED;self.db.commit();self.denied(409,**identity)
            self.game.status=GameStatus.RUNNING;self.obj.active=False;self.db.commit();self.denied(404,**identity)
            self.obj.active=True;self.db.commit()
        self.assertEqual(self.db.query(ScoreEvent).count(),0)

    def test_identifier_validation_and_round_scoping(self):
        for invalid in ({},{'duck_number':0},{'duck_number':21},{'duck_number':1.5},{'duck_number':True},{'duck_number':3,'serial_number':'0481641c460289'},{'serial_number':'https://invalid.example'}):
            with self.assertRaises(ValidationError): ScanInput(**invalid)
        other_game=Game(name='Other',status=GameStatus.RUNNING);self.db.add(other_game);self.db.flush()
        obj=GameObject(game_id=other_game.id,type=ObjectType.PHYSICAL_DUCK,name='Other duck',latitude=51.9,longitude=4.3)
        self.db.add(obj);self.db.flush()
        self.db.add(Duck(game_object_id=obj.id,duck_number=3,nfc_serial_hash=self.duck.nfc_serial_hash,scan_token_hash=hash_token('other-round-token')));self.db.commit()
        self.assertEqual(self.claim(duck_number=3)['name'],'Eend 3')
        self.denied(404,token='other-round-token')

    def test_installation_preserves_history_and_can_restore_old_field(self):
        install_boards(self.db);self.db.commit()
        game=self.db.query(Game).filter_by(game_code='RONDE-A').one()
        old={o.id for o in self.db.query(GameObject).filter_by(game_id=game.id,active=True)}
        self.claim(duck_number=3)
        install_boards(self.db,PACK);self.db.commit()
        self.assertEqual(self.db.query(GameObject).filter_by(game_id=game.id,active=True).count(),46)
        self.assertEqual(self.db.query(Duck).join(GameObject).filter(GameObject.game_id==game.id).count(),20)
        self.assertTrue(all(r['skipped'] for r in install_boards(self.db,PACK)))
        restore_boards(self.db,PACK['version']);self.db.commit()
        self.assertEqual({o.id for o in self.db.query(GameObject).filter_by(game_id=game.id,active=True)},old)
        self.assertEqual(self.db.query(ScoreEvent).one().points,50)

    def test_admin_catalog_create_move_replace_and_duplicate_guard(self):
        choices=available_ducks(self.game.id,self.admin,self.db)
        self.assertEqual(len(choices),20)
        self.assertEqual(next(d for d in choices if d['number']==3)['object_id'],self.obj.id)
        self.assertTrue(all('nfc_serial_hash' not in d for d in choices))
        def add(number):
            return asyncio.run(create_game_object(GameObjectInput(game_id=self.game.id,type='PHYSICAL_DUCK',name='Ignored name',duck_number=number,latitude=51.9,longitude=4.3),self.admin,self.db))
        with self.assertRaises(HTTPException) as denied:add(3)
        self.assertEqual(denied.exception.status_code,409)
        created=add(4);self.assertIn('Eend 4',created['name'])
        def move(number):
            return asyncio.run(move_duck(self.obj.id,DuckLocationInput(duck_number=number,latitude=51.901,longitude=4.301),self.game.id,self.admin,self.db))
        with self.assertRaises(HTTPException) as denied:move(4)
        self.assertEqual(denied.exception.status_code,409)
        self.claim(duck_number=3)
        moved=move(3);self.assertEqual(moved['id'],self.obj.id)
        self.assertEqual(self.obj.latitude,51.901)
        self.locate(lat=51.901,lng=4.301);self.denied(409,duck_number=3)
        replaced=move(5);self.assertNotEqual(replaced['id'],self.obj.id)
        self.assertFalse(self.obj.active)
        # Restoring an old physical duck reuses its score history.
        restored=add(3);self.assertEqual(restored['id'],self.obj.id)
        self.locate();self.denied(409,duck_number=3)

    def test_load_buttons_only_change_selected_round_and_retain_duck_claims(self):
        self.claim(duck_number=3)
        payload=LoadLocationsInput(layout='A')
        with self.assertRaises(HTTPException) as denied:asyncio.run(load_locations(self.game.id,payload,self.admin,self.db))
        self.assertEqual(denied.exception.status_code,409)
        self.game.status=GameStatus.PAUSED;self.db.commit()
        other=Game(name='Untouched',status=GameStatus.PAUSED,timer_remaining_seconds=23);self.db.add(other);self.db.commit()
        for layout in ('A','A','B'):
            result=asyncio.run(load_locations(self.game.id,LoadLocationsInput(layout=layout),self.admin,self.db))
            self.assertEqual(result['objects'],46);self.assertEqual(result['ducks'],20)
            self.assertEqual(self.db.query(GameObject).filter_by(game_id=self.game.id,active=True).count(),46)
            self.assertEqual(self.db.query(Duck).join(GameObject).filter(GameObject.game_id==self.game.id).count(),20)
        self.assertEqual(self.game.name,'Round');self.assertEqual(self.game.status,GameStatus.READY)
        self.assertEqual(other.status,GameStatus.PAUSED);self.assertEqual(other.timer_remaining_seconds,23)
        self.assertEqual(self.db.query(ScoreEvent).one().points,50)
        self.game.status=GameStatus.RUNNING;self.db.commit()
        self.locate(lat=self.obj.latitude,lng=self.obj.longitude);self.denied(409,duck_number=3)

class WalkableBoardTests(TestCase):
    def test_twenty_physical_ducks_shared_across_rounds(self):
        identities=[]
        for board in PACK['boards']:
            ducks=[o for o in board['objects'] if o['type']=='PHYSICAL_DUCK']
            self.assertEqual([o['duck_number'] for o in ducks],list(range(1,21)))
            self.assertEqual(len({o['nfc_serial_hash'] for o in ducks}),20)
            identities.append([(o['duck_number'],o['latitude'],o['longitude'],o['nfc_serial_hash']) for o in ducks])
        self.assertEqual(identities[0],identities[1])

    def test_routes_fit_twenty_minutes_from_hq_and_thirty_across_field(self):
        network=json.loads((PACK_FILE.parent/'allart_walk_routes.json').read_text())
        graph={}
        for a,b,w in network['edges']:
            graph.setdefault(a,[]).append((b,w));graph.setdefault(b,[]).append((a,w))
        def paths(start):
            costs={start:0};queue=[(0,start)]
            while queue:
                cost,node=heapq.heappop(queue)
                if costs[node]!=cost:continue
                for other,w in graph[node]:
                    if cost+w<costs.get(other,float('inf')):
                        costs[other]=cost+w;heapq.heappush(queue,(cost+w,other))
            return costs
        points=PACK['boards'][0]['objects'];allowance=PACK['walking']['route_allowance_m']
        from_hq=paths(network['hq_node_id'])
        for point in points:
            self.assertLessEqual(from_hq[point['osm_node_id']]+network['hq_offset_m']+allowance,4_000/60*20)
            to_other=paths(point['osm_node_id'])
            for other in points:self.assertLessEqual(to_other[other['osm_node_id']]+allowance,4_000/60*30)
