from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./cyberjoti.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "unsafe-development-secret"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173"
    location_ttl_seconds: int = 180
    maximum_accuracy: float = 50

    def model_post_init(self, __context: object) -> None:
        # Railway supplies postgresql://; SQLAlchemy here uses psycopg v3.
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache
def settings() -> Settings:
    return Settings()
