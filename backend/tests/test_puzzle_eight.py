from sqlalchemy.pool import StaticPool
import importlib.util
import json
from pathlib import Path
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Game, GameObject, ObjectType, Puzzle, Team, ScoreEvent, ScoreType
from app.security import verify_password

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('puzzle_eight', ROOT / 'alembic/versions/0013_puzzle_eight.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class PuzzleEightTests(unittest.TestCase):
    def test_all_default_packs_contain_the_correct_code_puzzles(self):
        answers = {'RONDE-A': 'scouting', 'RONDE-B': 'netwerk'}
        for path in (ROOT / 'app/data').glob('allart_joti_2026_*.json'):
            for board in json.loads(path.read_text(encoding='utf-8')).get('boards', []):
                if board['code'] not in answers:
                    continue
                puzzle = [obj for obj in board['objects'] if obj['type'] == 'PUZZLE'][7]
                self.assertTrue(verify_password(answers[board['code']], puzzle['answer_hash']))
                self.assertEqual(puzzle['question'], migration.CHANGES[board['code']]['question'])
        self.assertEqual(''.join(chr((ord(c) - ord('A') - 3) % 26 + ord('A')) for c in 'VFRXWLQJ'), 'SCOUTING')
        self.assertEqual('KREWTEN'[::-1], 'NETWERK')

    def test_migration_replaces_only_p8_and_preserves_progress(self):
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            game = Game(name='Ronde-A', game_code='RONDE-A')
            db.add(game); db.flush()
            team = Team(game_id=game.id, name='Team')
            db.add(team); db.flush()
            objects = [GameObject(game_id=game.id, type=ObjectType.PUZZLE, name=name, latitude=52, longitude=4) for name in ('P8 Puzzel Veilig wereldcontact', 'P8 Puzzel Iedereen welkom', 'P1 Puzzel Scoutcode')]
            db.add_all(objects); db.flush()
            puzzles = [Puzzle(game_object_id=obj.id, question='Old question', answer_hash='old', reward_points=500) for obj in objects]
            db.add_all(puzzles); db.flush()
            db.add(ScoreEvent(team_id=team.id, type=ScoreType.PUZZLE_SOLVED, reference_id=puzzles[0].id, points=500))
            db.commit()
            migration.apply_updates(db); db.commit(); db.expire_all()
            self.assertTrue(verify_password('scouting', puzzles[0].answer_hash))
            self.assertTrue(verify_password('netwerk', puzzles[1].answer_hash))
            self.assertEqual(puzzles[2].question, 'Old question')
            self.assertEqual(puzzles[0].reward_points, 500)
            self.assertEqual(db.query(ScoreEvent).one().reference_id, puzzles[0].id)
        engine.dispose()


if __name__ == '__main__':
    unittest.main()
