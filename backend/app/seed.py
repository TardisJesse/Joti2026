"""Idempotent local demo data; never run this against a production database."""
import os, secrets
from .database import Base, SessionLocal, engine
from .models import *
from .security import hash_password
from .services import hash_token

def main():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(User).first(): return
        game = Game(name="CyberJoti ontwikkeling", status=GameStatus.RUNNING); db.add(game); db.flush()
        valk = Team(game_id=game.id, name="De Valken", color="#00f0ff"); uilen = Team(game_id=game.id, name="De Uilen", color="#a855f7"); db.add_all([valk, uilen]); db.flush()
        db.add_all([User(name="admin", role=UserRole.ADMIN, password_hash=hash_password("admin-change-me")), User(name="valk", team_id=valk.id, role=UserRole.TEAM_LEADER, password_hash=hash_password("valk-change-me"))])
        puzzle_object = GameObject(game_id=game.id, type=ObjectType.PUZZLE, name="Crypto Node Bravo", description="Decodeer de Allart-code.", latitude=52.349, longitude=4.63, activation_radius_meters=50)
        capture_object = GameObject(game_id=game.id, type=ObjectType.CAPTURE_POINT, name="Radar Post", description="Houd de post bezet.", latitude=52.3494, longitude=4.6304, activation_radius_meters=40)
        duck_object = GameObject(game_id=game.id, type=ObjectType.PHYSICAL_DUCK, name="Ducktor Byte", description="Zoek de NFC-eend.", latitude=52.3487, longitude=4.6295, activation_radius_meters=60)
        db.add_all([puzzle_object, capture_object, duck_object]); db.flush()
        db.add(Puzzle(game_object_id=puzzle_object.id, question="Welke vogel is de mascotte van Scouting Allart?", answer_hash=hash_password("valk"), reward_points=500))
        db.add(CapturePoint(game_object_id=capture_object.id, capture_seconds=60, cooldown_seconds=300, capture_reward=250))
        token = os.environ.get("DEMO_DUCK_TOKEN", secrets.token_urlsafe(24)); db.add(Duck(game_object_id=duck_object.id, scan_token_hash=hash_token(token), reward_points=750, search_radius_meters=60))
        db.commit(); print(f"Development duck token: {token}")
    finally: db.close()
if __name__ == "__main__": main()
