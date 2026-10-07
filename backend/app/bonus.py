"""Rotating bonuses use persisted playing time, never a browser's clock."""
from datetime import datetime, timezone, timedelta
from .models import GameStatus

INTERVAL = 600
DURATION = 300
MULTIPLIER = 2


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def elapsed_time(game, at):
    elapsed = game.bonus_elapsed_seconds or 0
    if game.status == GameStatus.RUNNING and game.bonus_updated_at:
        end = min(at, utc(game.ends_at)) if game.ends_at else at
        elapsed += max(0, (end - utc(game.bonus_updated_at)).total_seconds())
    return elapsed


def bonus_seconds_until(seconds, index, count):
    """Total bonus seconds for a post, including arbitrarily long offline gaps."""
    if seconds <= 0 or not count:
        return 0
    cycle = int(seconds // INTERVAL)
    full_cycles = max(0, cycle - 1)
    occurrences = max(0, (full_cycles - index + count - 1) // count)
    partial = min(DURATION, seconds % INTERVAL) if cycle >= 1 and (cycle - 1) % count == index else 0
    return occurrences * DURATION + partial


def bonus_state(game, object_ids, at=None):
    at = at or datetime.now(timezone.utc)
    seconds = elapsed_time(game, at)
    cycle, offset = divmod(seconds, INTERVAL)
    if game.status != GameStatus.RUNNING or not object_ids or cycle < 1 or offset >= DURATION or (game.ends_at and utc(game.ends_at) <= at):
        return None
    return {'object_id': object_ids[(int(cycle) - 1) % len(object_ids)],
            'multiplier': MULTIPLIER,
            'ends_at': (at + timedelta(seconds=DURATION - offset)).isoformat(),
            'cycle': int(cycle)}
