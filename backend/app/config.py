from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    database_url: str = "postgresql://attendance_user:attendance_pass@localhost:5432/smart_attendance"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 480
    cookie_secure: bool = False
    face_recognition_threshold: float = 0.363
    face_min_samples: int = 10
    face_max_samples: int = 20
    frontend_url: str = "http://localhost:5173"
    upload_dir: str = "uploads"
    algorithm: str = "HS256"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_dirs(settings: Settings) -> None:
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "photos"), exist_ok=True)
    os.makedirs(os.path.join(settings.upload_dir, "models"), exist_ok=True)
