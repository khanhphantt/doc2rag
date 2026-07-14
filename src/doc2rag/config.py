from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOC2RAG_", extra="ignore")

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"

    ocr_lang: str = "japan"
    ocr_confidence_threshold: float = 0.80

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "doc2rag"
    mongo_chunks_collection: str = "checkup_chunks"

    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    pdf_render_dpi: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
