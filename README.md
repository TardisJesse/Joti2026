<<<<<<< HEAD
# Joti2026
=======
# CyberJoti

Location-based JOTI game for teams at Scouting Allart van Heemstede. The backend is authoritative: browsers may share their position but cannot award their own points.

## Run locally

1. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`.
2. Start the full stack with `docker compose up --build`.
3. Open http://localhost:5173 and log in with the seeded development accounts:
   - `admin` / `admin-change-me`
   - `valk` / `valk-change-me`

API docs are available at http://localhost:8000/docs. The development seed adds a running game, two teams, a puzzle, capture point, and duck. The duck scan token is printed in the backend seed log.

## Useful commands

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
docker compose down -v  # removes local database data
```

Do not use development credentials or the sample secret in staging/production.
>>>>>>> b886f0e (Add initial project configuration files for PyCharm and basic Python script)
