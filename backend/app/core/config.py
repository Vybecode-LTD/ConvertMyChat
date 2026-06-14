"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ConvertMyChat API"
    debug: bool = False

    # Database (Railway Postgres)
    database_url: str = "postgresql+asyncpg://localhost:5432/convertmychat"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/auth/callback"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Scraping
    max_concurrent_scrapes: int = 2
    scrape_timeout_ms: int = 30000

    # Cache TTL in seconds (24 hours)
    cache_ttl_seconds: int = 86400

    # Admin
    admin_email: str = ""  # First admin account email

    @property
    def async_database_url(self) -> str:
        """Normalize DATABASE_URL for asyncpg.

        Railway gives postgresql://... but SQLAlchemy async needs
        postgresql+asyncpg://... — the #1 cause of deploy failures.
        """
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
