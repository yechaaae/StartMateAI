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
    rag_retrieval_mode: str
    rag_vector_store_path: str
    support_rag_embedding_dimensions: int
    support_rag_chroma_enabled: bool
    support_rag_chroma_path: str
    support_rag_chroma_collection: str
    rag_chroma_path: str
    rag_embedding_dimensions: int
    rag_embedding_provider: str
    openai_embedding_base_url: str
    openai_embedding_path: str
    openai_embedding_model: str
    gms_api_key: str
    gms_base_url: str
    gms_chat_path: str
    gms_model: str
    gms_api_key_header: str
    gms_api_key_query_param: str
    gms_auth_scheme: str
    gms_timeout_seconds: float
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_username: str
    rabbitmq_password: str
    ai_chat_request_queue: str
    ai_chat_response_queue: str
    backend_internal_base_url: str
    internal_tool_token: str
    backend_tool_timeout_seconds: float


@lru_cache
def get_settings() -> Settings:
    api_key = os.getenv("GMS_API_KEY", "")
    base_url = os.getenv("GMS_BASE_URL", "")
    return Settings(
        app_name=os.getenv("APP_NAME", "StartMate AI"),
        use_mock_llm=_env_bool("USE_MOCK_LLM", default=not bool(api_key and base_url)),
        rag_retrieval_mode=os.getenv("RAG_RETRIEVAL_MODE", "hybrid").strip().lower(),
        rag_vector_store_path=os.getenv("RAG_VECTOR_STORE_PATH", ""),
        support_rag_embedding_dimensions=int(os.getenv("SUPPORT_RAG_EMBEDDING_DIMENSIONS", "384")),
        support_rag_chroma_enabled=_env_bool("SUPPORT_RAG_CHROMA_ENABLED", default=False),
        support_rag_chroma_path=os.getenv("SUPPORT_RAG_CHROMA_PATH", os.getenv("RAG_CHROMA_PATH", ".chroma")),
        support_rag_chroma_collection=os.getenv("SUPPORT_RAG_CHROMA_COLLECTION", "support_programs"),
        rag_chroma_path=os.getenv("RAG_CHROMA_PATH", ".chroma"),
        rag_embedding_dimensions=int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "384")),
        rag_embedding_provider=os.getenv("RAG_EMBEDDING_PROVIDER", "hash").strip().lower(),
        openai_embedding_base_url=os.getenv(
            "OPENAI_EMBEDDING_BASE_URL",
            "https://gms.ssafy.io/gmsapi/api.openai.com",
        ).strip(),
        openai_embedding_path=os.getenv("OPENAI_EMBEDDING_PATH", "/v1/embeddings").strip(),
        openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large").strip(),
        gms_api_key=api_key,
        gms_base_url=base_url or "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com",
        gms_chat_path=os.getenv("GMS_CHAT_PATH", "/v1beta/models/gemini-2.5-flash:generateContent"),
        gms_model=os.getenv("GMS_MODEL", "gemini-2.5-flash"),
        gms_api_key_header=os.getenv("GMS_API_KEY_HEADER", "x-goog-api-key"),
        gms_api_key_query_param=os.getenv("GMS_API_KEY_QUERY_PARAM", ""),
        gms_auth_scheme=os.getenv("GMS_AUTH_SCHEME", ""),
        gms_timeout_seconds=float(os.getenv("GMS_TIMEOUT_SECONDS", "30")),
        rabbitmq_host=os.getenv("SPRING_RABBITMQ_HOST", os.getenv("RABBITMQ_HOST", "rabbitmq")),
        rabbitmq_port=int(os.getenv("SPRING_RABBITMQ_PORT", os.getenv("RABBITMQ_PORT", "5672"))),
        rabbitmq_username=os.getenv("SPRING_RABBITMQ_USERNAME", os.getenv("RABBITMQ_USERNAME", "startmate")),
        rabbitmq_password=os.getenv("SPRING_RABBITMQ_PASSWORD", os.getenv("RABBITMQ_PASSWORD", "startmate")),
        ai_chat_request_queue=os.getenv("STARTMATE_AI_CHAT_REQUEST_QUEUE", "chat.request"),
        ai_chat_response_queue=os.getenv("STARTMATE_AI_CHAT_RESPONSE_QUEUE", "chat.response"),
        backend_internal_base_url=os.getenv("BACKEND_INTERNAL_BASE_URL", "http://backend:8080").rstrip("/"),
        internal_tool_token=os.getenv("STARTMATE_INTERNAL_TOOL_TOKEN", "startmate-local-internal-token"),
        backend_tool_timeout_seconds=float(os.getenv("BACKEND_TOOL_TIMEOUT_SECONDS", "10")),
    )
