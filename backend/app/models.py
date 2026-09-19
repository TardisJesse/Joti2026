import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class IdTimeMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GameStatus(str, enum.Enum): DRAFT="DRAFT"; READY="READY"; RUNNING="RUNNING"; PAUSED="PAUSED"; FINISHED="FINISHED"
class UserRole(str, enum.Enum): PLAYER="PLAYER"; TEAM_LEADER="TEAM_LEADER"; ADMIN="ADMIN"
class ObjectType(str, enum.Enum): PUZZLE="PUZZLE"; CAPTURE_POINT="CAPTURE_POINT"; PHYSICAL_DUCK="PHYSICAL_DUCK"
class ScoreType(str, enum.Enum): PUZZLE_SOLVED="PUZZLE_SOLVED"; CAPTURE_COMPLETED="CAPTURE_COMPLETED"; DUCK_FOUND="DUCK_FOUND"; ADMIN_ADJUSTMENT="ADMIN_ADJUSTMENT"


class Game(IdTimeMixin, Base):
    __tablename__ = "games"
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus), default=GameStatus.DRAFT, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Team(IdTimeMixin, Base):
    __tablename__ = "teams"
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#00f0ff")


class User(IdTimeMixin, Base):
    __tablename__ = "users"
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.PLAYER)
    password_hash: Mapped[str] = mapped_column(String(512))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class GameObject(IdTimeMixin, Base):
    __tablename__ = "game_objects"
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    type: Mapped[ObjectType] = mapped_column(Enum(ObjectType), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    activation_radius_meters: Mapped[int] = mapped_column(Integer, default=40)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Puzzle(IdTimeMixin, Base):
    __tablename__ = "puzzles"
    game_object_id: Mapped[str] = mapped_column(ForeignKey("game_objects.id", ondelete="CASCADE"), unique=True)
    question: Mapped[str] = mapped_column(Text)
    answer_hash: Mapped[str] = mapped_column(String(512))
    reward_points: Mapped[int] = mapped_column(Integer)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CapturePoint(IdTimeMixin, Base):
    __tablename__ = "capture_points"
    game_object_id: Mapped[str] = mapped_column(ForeignKey("game_objects.id", ondelete="CASCADE"), unique=True)
    capture_seconds: Mapped[int] = mapped_column(Integer, default=60)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300)
    capture_reward: Mapped[int] = mapped_column(Integer, default=250)
    owner_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)


class Duck(IdTimeMixin, Base):
    __tablename__ = "ducks"
    game_object_id: Mapped[str] = mapped_column(ForeignKey("game_objects.id", ondelete="CASCADE"), unique=True)
    scan_token_hash: Mapped[str] = mapped_column(String(512), unique=True)
    reward_points: Mapped[int] = mapped_column(Integer, default=500)
    search_radius_meters: Mapped[int] = mapped_column(Integer, default=50)


class PuzzleAttempt(IdTimeMixin, Base):
    __tablename__ = "puzzle_attempts"
    puzzle_id: Mapped[str] = mapped_column(ForeignKey("puzzles.id"), index=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    correct: Mapped[bool] = mapped_column(Boolean)


class CaptureEvent(IdTimeMixin, Base):
    __tablename__ = "capture_events"
    capture_point_id: Mapped[str] = mapped_column(ForeignKey("capture_points.id"), index=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    event: Mapped[str] = mapped_column(String(30))


class DuckScan(IdTimeMixin, Base):
    __tablename__ = "duck_scans"
    __table_args__ = (UniqueConstraint("duck_id", "team_id", name="uq_duck_scan_team"),)
    duck_id: Mapped[str] = mapped_column(ForeignKey("ducks.id"), index=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class ScoreEvent(IdTimeMixin, Base):
    __tablename__ = "score_events"
    __table_args__ = (UniqueConstraint("team_id", "type", "reference_id", name="uq_score_reward"),)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    type: Mapped[ScoreType] = mapped_column(Enum(ScoreType))
    points: Mapped[int] = mapped_column(Integer)
    reference_id: Mapped[str] = mapped_column(String(36), index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
