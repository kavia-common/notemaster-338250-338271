import os
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Settings:
    """Application settings resolved from environment variables.

    Contract:
    - Inputs: environment variables (POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT)
    - Outputs: normalized, typed settings, including an async SQLAlchemy database URL.
    - Errors: ValueError when required DB settings are missing.
    """

    postgres_url: str | None
    postgres_user: str | None
    postgres_password: str | None
    postgres_db: str | None
    postgres_port: str | None

    @property
    def sqlalchemy_async_database_url(self) -> str:
        """Build an async SQLAlchemy URL for psycopg (PostgreSQL)."""
        # Prefer explicit URL if provided.
        if self.postgres_url:
            url = self.postgres_url.strip()
            if url.startswith("postgresql+psycopg://"):
                return url
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+psycopg://", 1)
            # If someone provides a host-only URL, we don't guess the format.
            raise ValueError(
                "POSTGRES_URL must start with 'postgresql://' or 'postgresql+psycopg://'"
            )

        # Otherwise, compose from parts.
        missing = [
            name
            for name, val in [
                ("POSTGRES_USER", self.postgres_user),
                ("POSTGRES_PASSWORD", self.postgres_password),
                ("POSTGRES_DB", self.postgres_db),
                ("POSTGRES_PORT", self.postgres_port),
            ]
            if not val
        ]
        if missing:
            raise ValueError(
                f"Database configuration missing required variables: {', '.join(missing)}"
            )

        host = "localhost"
        user = quote_plus(self.postgres_user or "")
        password = quote_plus(self.postgres_password or "")
        db = quote_plus(self.postgres_db or "")
        port = quote_plus(self.postgres_port or "")
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load settings from environment.

    Returns:
        Settings: Normalized settings object.

    Raises:
        ValueError: When DB configuration is incomplete or invalid.
    """
    return Settings(
        postgres_url=os.getenv("POSTGRES_URL"),
        postgres_user=os.getenv("POSTGRES_USER"),
        postgres_password=os.getenv("POSTGRES_PASSWORD"),
        postgres_db=os.getenv("POSTGRES_DB"),
        postgres_port=os.getenv("POSTGRES_PORT"),
    )
