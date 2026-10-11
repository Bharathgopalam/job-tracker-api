"""Application settings, read from environment variables."""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from functools import lru_cache

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    token_minutes: int
    password_iterations: int
    algorithm: str = "HS256"


@lru_cache
def get_settings() -> Settings:
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        # Never ship a hard-coded default secret. An ephemeral key is safe but invalidates
        # tokens on restart, which is the right failure mode for a missing configuration.
        log.warning("SECRET_KEY is not set; using an ephemeral key. Tokens reset on restart.")
        secret = secrets.token_urlsafe(48)
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "sqlite:///./jobtracker.db"),
        secret_key=secret,
        token_minutes=int(os.environ.get("TOKEN_MINUTES", "60")),
        password_iterations=int(os.environ.get("PASSWORD_ITERATIONS", "310000")),
    )
