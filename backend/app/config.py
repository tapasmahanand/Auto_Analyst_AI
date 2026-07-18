from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    storage_dir: Path = PROJECT_ROOT / "storage"
    max_upload_mb: int = 50
    exec_timeout_seconds: int = 60
    exec_memory_mb: int = 2048
    max_code_retries: int = 3
    max_plan_steps: int = 6
    cors_origins: str = "http://localhost:3000"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def runs_dir(self) -> Path:
        return self.storage_dir / "runs"

    @property
    def reports_dir(self) -> Path:
        return self.storage_dir / "reports"

    @property
    def db_path(self) -> Path:
        return self.storage_dir / "autoanalyst.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for d in (self.storage_dir, self.uploads_dir, self.runs_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
