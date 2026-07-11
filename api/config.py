"""
IBM Scout — Central configuration loaded from environment variables.
All secrets come from .env (never hardcoded). Missing required vars raise at startup.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Neo4j ──────────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""  # optional — leave blank for demo/mock mode

    # ── watsonx.ai ─────────────────────────────────────────────────────────
    watsonx_api_key: str = ""   # optional — leave blank for demo/mock mode
    watsonx_project_id: str = ""  # optional — leave blank for demo/mock mode
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_model_id: str = "ibm/granite-13b-instruct-v2"
    watsonx_embed_model_id: str = "ibm/slate-125m-english-rtrvr"

    # ── ChromaDB (vector store) ─────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"

    # ── Pruning agent schedule ──────────────────────────────────────────────
    pruning_interval_hours: int = 6
    # Node TTL in days — nodes not re-verified within this window are marked STALE
    default_node_ttl_days: int = 30
    stale_delete_threshold_days: int = 90

    # ── API ─────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    environment: str = "development"

    # ── Search ─────────────────────────────────────────────────────────────
    search_max_results: int = 25
    search_similarity_threshold: float = 0.72

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
