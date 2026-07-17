from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings' env_file loading below only populates this module's own
# Settings fields; it doesn't export .env into the process environment. This
# is needed separately for GOOGLE_APPLICATION_CREDENTIALS, which google-auth
# reads directly from os.environ, not through Settings (see .env.example).
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOC2RAG_", extra="ignore")

    # PaddleOCR-VL core engine
    vl_pipeline_version: str = "v1.6"

    # LLM (medical advisor / legacy structuring)
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"

    # Legacy Document AI pipeline (retained, not used by the PaddleOCR-VL baseline)
    gcp_project_id: str = ""
    gcp_location: str = "us"
    docai_processor_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
