"""Application settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # RAG
    chroma_persist_dir: str = "./data/chroma"

    # Agent
    max_agent_iterations: int = 10
    mcp_config_path: str = "omnibot.json"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
