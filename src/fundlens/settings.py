"""Every environment variable fundlens reads, in one place (spec §10.1).

Later tickets add their own settings here (Cloudflare, DeepInfra, telemetry, DuckDB limits)
rather than reading `os.environ` where they are used.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")

    # R2 in prod, MinIO in dev and CI: the same S3 client, pointed at a different endpoint.
    r2_endpoint: str = Field(..., alias="R2_ENDPOINT")
    r2_access_key_id: str = Field(..., alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: SecretStr = Field(..., alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="fundlens-data", alias="R2_BUCKET")
    r2_public_bucket: str = Field(default="fundlens-public", alias="R2_PUBLIC_BUCKET")

    # Root of the local cache volumes (bronze/, silver/, scratch/, resolution/; spec §3.4).
    data_dir: Path = Field(default=Path("/data/fundlens"), alias="DATA_DIR")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
