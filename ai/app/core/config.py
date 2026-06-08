from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    use_mock_llm: bool
    gms_api_key: str
    gms_base_url: str
    gms_chat_path: str
    gms_model: str
    gms_api_key_header: str
    gms_api_key_query_param: str
    gms_auth_scheme: str
    gms_timeout_seconds: float


@lru_cache
def get_settings() -> Settings:
    api_key = os.getenv("GMS_API_KEY", "")
    base_url = os.getenv("GMS_BASE_URL", "")
    return Settings(
        app_name=os.getenv("APP_NAME", "StartMate AI"),
        use_mock_llm=_env_bool("USE_MOCK_LLM", default=not bool(api_key and base_url)),
        gms_api_key=api_key,
        gms_base_url=base_url or "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com",
        gms_chat_path=os.getenv("GMS_CHAT_PATH", "/v1beta/models/gemini-2.5-flash:generateContent"),
        gms_model=os.getenv("GMS_MODEL", "gemini-2.5-flash"),
        gms_api_key_header=os.getenv("GMS_API_KEY_HEADER", "x-goog-api-key"),
        gms_api_key_query_param=os.getenv("GMS_API_KEY_QUERY_PARAM", ""),
        gms_auth_scheme=os.getenv("GMS_AUTH_SCHEME", ""),
        gms_timeout_seconds=float(os.getenv("GMS_TIMEOUT_SECONDS", "30")),
    )
