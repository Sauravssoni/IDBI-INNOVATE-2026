import os
import urllib.parse
from typing import List


def is_localhost_origin(origin: str) -> bool:
    try:
        val = origin.strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = "http://" + val
        parsed = urllib.parse.urlparse(val)
        hostname = (parsed.hostname or "").lower()
        return hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0")  # nosec B104
    except Exception:
        return False


class Settings:
    def __init__(self):
        self.APP_ENV: str = os.getenv("APP_ENV", "development").lower()

        raw_demo_access = os.getenv("DEMO_ACCESS_ENABLED", "false").lower()
        self.DEMO_ACCESS_ENABLED: bool = raw_demo_access in ("true", "1", "t", "yes")

        raw_origins = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS")
        if self.APP_ENV == "production" and (
            raw_origins is None or raw_origins.strip() == ""
        ):
            raise RuntimeError("In production, explicit ALLOWED_ORIGINS required")

        if raw_origins is not None and raw_origins.strip() != "":
            self.ALLOWED_ORIGINS: List[str] = [
                o.strip() for o in raw_origins.split(",") if o.strip()
            ]
        else:
            self.ALLOWED_ORIGINS: List[str] = [
                "http://localhost:3005",
                "http://127.0.0.1:3005",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]

        if not self.ALLOWED_ORIGINS:
            raise RuntimeError("ALLOWED_ORIGINS cannot be empty")

        raw_cookie_secure = os.getenv("COOKIE_SECURE")
        if raw_cookie_secure is not None:
            val = raw_cookie_secure.strip().lower()
            if val in ("true", "1", "t", "yes"):
                self.COOKIE_SECURE: bool = True
            elif val in ("false", "0", "f", "no"):
                self.COOKIE_SECURE: bool = False
            else:
                self.COOKIE_SECURE: bool = self.APP_ENV != "development"
        else:
            self.COOKIE_SECURE: bool = self.APP_ENV != "development"

        if self.APP_ENV == "production":
            if not self.COOKIE_SECURE:
                raise RuntimeError("In production, COOKIE_SECURE=true required")
            for origin in self.ALLOWED_ORIGINS:
                if origin == "*" or "*" in origin:
                    raise RuntimeError(
                        "In production, wildcard origins are not permitted"
                    )
                if not origin.strip().lower().startswith("https://"):
                    raise RuntimeError("In production, explicit HTTPS origins required")
                if is_localhost_origin(origin):
                    raise RuntimeError(
                        "In production, localhost origins are not permitted"
                    )

        if not self.COOKIE_SECURE:
            if self.APP_ENV != "development":
                raise RuntimeError(
                    "COOKIE_SECURE=false is only permitted when APP_ENV=development"
                )
            if not all(is_localhost_origin(o) for o in self.ALLOWED_ORIGINS):
                raise RuntimeError(
                    "COOKIE_SECURE=false is only permitted when every allowed origin is a recognized localhost origin"
                )

        def _clean_secret(val: str | None) -> str | None:
            if not val:
                return None
            val = val.strip().strip('"').strip("'")
            if not val or val.lower() in ("none", "null", "replace_this_with_a_secure_random_string_for_production", "change-this-local-development-password"):
                return None
            return val

        self.JWT_SECRET = _clean_secret(os.getenv("JWT_SECRET"))
        if self.APP_ENV == "production" and not self.JWT_SECRET:
            raise RuntimeError("In production, a valid JWT_SECRET is required")

        self.DEMO_USER_PASSWORD = _clean_secret(os.getenv("DEMO_USER_PASSWORD"))
        if self.APP_ENV == "production" and self.DEMO_ACCESS_ENABLED and not self.DEMO_USER_PASSWORD:
            raise RuntimeError("In production, DEMO_USER_PASSWORD is required when DEMO_ACCESS_ENABLED is true")


def get_settings() -> Settings:
    return Settings()
