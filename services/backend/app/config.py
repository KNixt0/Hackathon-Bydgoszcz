"""All configuration comes from environment variables (see Settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    # --- service ---
    backend_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = ""  # comma separated; empty = CORS disabled (same origin via nginx)

    # --- dependencies ---
    database_url: str = "sqlite:///./investwatch.db"
    redis_url: str = ""  # Valkey; empty = no broker (only valid with TASK_MODE != celery)
    ai_url: str = "http://ai:8001"
    ai_timeout_seconds: float = 180.0
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "investwatch"
    s3_region: str = "us-east-1"

    # --- queue ---
    task_mode: Literal["celery", "thread", "eager"] = "celery"
    scan_max_retries: int = 4
    scan_retry_backoff_seconds: float = 5.0
    rescan_cron: str = "0 */6 * * *"
    registry_refresh_cron: str = "30 3 * * *"

    # --- pipeline ---
    alert_threshold: float = 70.0
    samples_dir: str = "/samples"
    fixture_base_url: str = "http://backend:8000"
    seed_on_start: bool = False

    # --- scraper ---
    proxy_urls: str = ""  # comma separated, empty = direct
    scrape_timeout_seconds: float = 20.0
    scrape_retries: int = 2
    scrape_host_delay_seconds: float = 1.5
    scrape_max_bytes: int = 5_000_000
    respect_robots: bool = True
    playwright_enabled: bool = True
    chromium_no_sandbox: bool = True  # Chromium's own sandbox needs extra container privileges
    registry_min_entries: int = 3

    # --- exports ---
    csv_delimiter: str = ";"
    registry_max_pages: int = 60

    @field_validator("database_url")
    @classmethod
    def _pg_driver(cls, value: str) -> str:
        # Only the BSD-licensed pg8000 driver is shipped (psycopg is LGPL).
        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://", "postgresql+psycopg://"):
            if value.startswith(prefix):
                return "postgresql+pg8000://" + value[len(prefix) :]
        return value

    @field_validator("fixture_base_url", "ai_url")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def proxy_list(self) -> list[str]:
        return [p.strip() for p in self.proxy_urls.split(",") if p.strip()]

    @property
    def fixture_origin(self) -> tuple[str, str, int]:
        parts = urlsplit(self.fixture_base_url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
        return (parts.scheme, (parts.hostname or "").lower(), port)


@lru_cache
def get_settings() -> Settings:
    return Settings()
