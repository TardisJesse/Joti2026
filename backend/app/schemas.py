from datetime import datetime
from pydantic import BaseModel, Field

class LoginInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
class GameJoinInput(BaseModel):
    game_code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    team_name: str = Field(min_length=2, max_length=100)
class GameCreateInput(BaseModel):
    game_code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, max_length=160)
class GameStatusInput(BaseModel):
    status: str
class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(ge=0, le=500)
    timestamp: datetime | None = None
class AnswerInput(BaseModel): answer: str = Field(min_length=1, max_length=500)
class ScanInput(BaseModel): token: str = Field(min_length=16, max_length=256)

class GameObjectInput(BaseModel):
    game_id: str = Field(min_length=36, max_length=36)
    type: str
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    activation_radius_meters: int = Field(default=40, ge=5, le=1000)
    reward_points: int = Field(default=500, ge=0, le=100000)
    question: str | None = Field(default=None, max_length=2000)
    answer: str | None = Field(default=None, min_length=1, max_length=500)
    max_attempts: int | None = Field(default=None, ge=1, le=100)
    capture_seconds: int = Field(default=60, ge=5, le=3600)
    cooldown_seconds: int = Field(default=300, ge=0, le=86400)
    search_radius_meters: int = Field(default=50, ge=5, le=1000)
