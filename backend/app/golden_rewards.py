from datetime import datetime, timezone

from .bonus import utc
from .models import GameStatus


def golden_reward_window(game, at: datetime | None = None) -> bool:
    if game.status != GameStatus.RUNNING or not game.ends_at:
        return False
    remaining = (utc(game.ends_at) - (at or datetime.now(timezone.utc))).total_seconds()
    return 0 < remaining <= 15 * 60
