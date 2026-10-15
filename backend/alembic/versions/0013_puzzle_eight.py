"""Replace both eighth multiple-choice questions with word-code puzzles."""
from alembic import op
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models import GameObject, Puzzle, ObjectType

revision = '0013_puzzle_eight'
down_revision = '0012_field_updates'
branch_labels = None
depends_on = None

CHANGES = {'RONDE-A': {'name': 'P8 Puzzel De Caesarcode', 'question': 'Een Caesarcode schuift iedere letter 3 plaatsen vooruit: A wordt D, B wordt E en Z wordt C. Ontcijfer VFRXWLQJ door iedere letter 3 plaatsen terug te schuiven. Antwoord met alleen het woord.', 'old_names': ('Puzzel Veilig wereldcontact', 'P8 Puzzel Veilig wereldcontact'), 'answer_hash': '$argon2id$v=19$m=65536,t=3,p=4$A4rUm25C8Fe+Gpkgr8ai8Q$RCw25RCtr6LJyuWxX2nVRd5SQX+UmZWAr+DYZlQqezs', 'ids': ['b5669b3e-cf2c-5d32-b182-96b77f2aed21', '76f09114-03e8-555c-8ced-e5870d47f90b', 'a3fe6aea-72b9-5eec-ab9a-b9e3cdeedd6c']}, 'RONDE-B': {'name': 'P8 Puzzel Het spiegelbericht', 'question': 'Een geheime code schrijft woorden van achter naar voren. Voorbeeld: MAET wordt TEAM. Ontcijfer KREWTEN. Antwoord met alleen het Nederlandse woord.', 'old_names': ('Puzzel Iedereen welkom', 'P8 Puzzel Iedereen welkom'), 'answer_hash': '$argon2id$v=19$m=65536,t=3,p=4$kK7k5gY6gqCD3/0ItTGV3A$JfP0bkPdnMCy0ynWfY6cFIooXQ8ABCuGXNEDYkZps1I', 'ids': ['2bed2a44-0a45-5db8-b78a-4f0f6e12ed29', '49884ed2-aabc-598d-bf05-69ca8dca2009', 'b93fe8c8-7f76-54e3-a3ca-aedf9e43b6aa']}}


def apply_updates(db):
    count = 0
    for change in CHANGES.values():
        objects = db.query(GameObject).filter(GameObject.type == ObjectType.PUZZLE, or_(GameObject.id.in_(change['ids']), GameObject.name.in_(change['old_names']))).all()
        for obj in objects:
            puzzle = db.query(Puzzle).filter_by(game_object_id=obj.id).one_or_none()
            if puzzle is None:
                continue
            obj.name = change['name']
            puzzle.question = change['question']
            puzzle.answer_hash = change['answer_hash']
            count += 1
    db.flush()
    print('P8 code puzzles updated:', count)


def upgrade():
    with Session(bind=op.get_bind(), join_transaction_mode='create_savepoint') as db:
        apply_updates(db)
        db.commit()


def downgrade():
    # Keep team progress and the replacement questions on a code rollback.
    pass
