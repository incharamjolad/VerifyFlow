from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str = ""
    mongodb_db: str = "verifyflow"
    jwt_secret: str = "verifyflow-demo-secret-key-at-least-32-chars-long"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    max_upload_mb: int = 10

    @property
    def cors_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        for default_origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]:
            if default_origin not in origins:
                origins.append(default_origin)
        return origins


settings = Settings()
