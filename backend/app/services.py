import asyncio, hashlib, math, time
from collections import defaultdict
from typing import Any
from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError
from .config import settings

try: redis_client: Redis | None = Redis.from_url(settings().redis_url, decode_responses=True)
except RedisError: redis_client = None

memory_locations: dict[str, dict[str, Any]] = {}
capture_started: dict[tuple[str, str], float] = {}
cooldowns: dict[tuple[str, str], float] = {}
subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

def hash_token(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()
def distance_meters(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    r = 6371000
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat-a_lat), math.radians(b_lon-a_lon)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(h))
def set_location(user_id: str, value: dict[str, Any]):
    memory_locations[user_id] = value
    if redis_client:
        try: redis_client.hset(f"player:location:{user_id}", mapping=value); redis_client.expire(f"player:location:{user_id}", settings().location_ttl_seconds)
        except RedisError: pass
def get_location(user_id: str) -> dict[str, Any] | None:
    if redis_client:
        try:
            data = redis_client.hgetall(f"player:location:{user_id}")
            if data: return {**data, "lat": float(data["lat"]), "lng": float(data["lng"]), "accuracy": float(data["accuracy"])}
        except RedisError: pass
    return memory_locations.get(user_id)
def require_nearby(user_id: str, lat: float, lng: float, radius: int):
    loc = get_location(user_id)
    if not loc: raise HTTPException(409, "Share a recent GPS location first")
    if float(loc["accuracy"]) > settings().maximum_accuracy: raise HTTPException(409, "GPS accuracy is too low")
    if distance_meters(float(loc["lat"]), float(loc["lng"]), lat, lng) > radius: raise HTTPException(403, "You are outside the activation radius")
def begin_capture(point_id: str, team_id: str, cooldown_seconds: int):
    key = (point_id, team_id); now = time.monotonic()
    if cooldowns.get(key, 0) > now: raise HTTPException(409, "Capture point is cooling down")
    capture_started.setdefault(key, now)
    return capture_started[key]
def cancel_capture(point_id: str, team_id: str): capture_started.pop((point_id, team_id), None)
def complete_capture(point_id: str, team_id: str, duration: int, cooldown_seconds: int) -> bool:
    key = (point_id, team_id); started = capture_started.get(key)
    if not started or time.monotonic() - started < duration: return False
    capture_started.pop(key, None); cooldowns[key] = time.monotonic() + cooldown_seconds
    return True
async def broadcast(channel: str, event: dict):
    for queue in list(subscribers[channel]): await queue.put(event)
