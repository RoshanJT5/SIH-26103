from functools import lru_cache
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_here = Path(__file__).resolve()
if len(_here.parents) >= 4 and (_here.parents[3] / "requirements.txt").exists():
    PROJECT_ROOT = _here.parents[3]
elif len(_here.parents) >= 3 and (_here.parents[2] / "requirements.txt").exists():
    PROJECT_ROOT = _here.parents[2]
else:
    PROJECT_ROOT = _here.parents[3] if len(_here.parents) >= 4 else _here.parent



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SIH 26103 Project Monitoring"
    app_env: str = "development"
    log_level: str = "INFO"
    max_upload_bytes: int = 25 * 1024 * 1024
    database_url: str = "sqlite:///./database/project_monitoring.db"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    admin_username: str = ""
    admin_password: str = ""
    admin_token_ttl_seconds: int = 1800
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @computed_field
    @property
    def resolved_database_url(self) -> str:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return self.database_url
        raw_path = self.database_url[len(prefix) :]
        if raw_path == ":memory:" or raw_path.startswith("file:"):
            return self.database_url
        db_path = Path(raw_path)
        if not db_path.is_absolute():
            db_path = (PROJECT_ROOT / db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{db_path.as_posix()}"

    @computed_field
    @property
    def assistant_enabled(self) -> bool:
        return bool(self.groq_api_key.strip() and self.groq_model.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
