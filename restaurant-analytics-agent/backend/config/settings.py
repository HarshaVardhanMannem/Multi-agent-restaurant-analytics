"""
Application Settings Configuration
Loads environment variables and provides typed configuration
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database - supports multiple naming conventions
    database_url: str | None = None  # Primary: DATABASE_URL
    supabase_db_url: str | None = None  # Alternative: SUPABASE_DB_URL

    # Alternative Supabase config (will be converted to db_url)
    supabase_url: str | None = None
    supabase_key: str | None = None  # Not used for direct DB, but allowed
    supabase_password: str | None = None  # DB password

    # NVIDIA API
    nvidia_api_key: str
    nvidia_model: str = "ai-nemotron-3-nano-30b-a3b"
    nvidia_model_fast: str = "ai-nemotron-3-nano-30b-a3b"  # Same model for all agents

    # JWT Authentication
    jwt_secret_key: str | None = None  # Optional - will derive from nvidia_api_key if not set
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Query settings
    max_query_timeout: int = 30
    max_retries: int = 2

    # Logging
    log_level: str = "INFO"

    # Database pool settings
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20
    db_command_timeout: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    def get_database_url(self) -> str:
        """Get the database connection URL, constructing it if necessary"""
        # Priority 1: DATABASE_URL (most common convention)
        if self.database_url:
            return self.database_url

        # Priority 2: SUPABASE_DB_URL (Supabase-specific)
        if self.supabase_db_url:
            return self.supabase_db_url

        # Priority 3: Construct from SUPABASE_URL + SUPABASE_PASSWORD
        if self.supabase_url and self.supabase_password:
            # Extract project ref from URL like https://xxxxx.supabase.co
            project_ref = self.supabase_url.replace("https://", "").replace(".supabase.co", "")
            return f"postgresql://postgres:{self.supabase_password}@db.{project_ref}.supabase.co:5432/postgres"

        raise ValueError(
            "Database URL not configured. Please set one of the following:\n"
            "  1. DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres\n"
            "  2. SUPABASE_DB_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres\n"
            "  3. SUPABASE_URL=https://PROJECT.supabase.co + SUPABASE_PASSWORD=YOUR_PASSWORD"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
