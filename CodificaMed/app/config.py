"""Configuración exclusivamente para CodificaMed (no se incluye .env en la entrega)."""
import os
from pathlib import Path
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

class Settings:
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip()
        self.ollama_num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
        self.ollama_timeout = float(os.getenv("OLLAMA_TIMEOUT", "180"))
        self.embeddings_provider = os.getenv("EMBEDDINGS_PROVIDER", "lexico").strip().lower()
        self.embeddings_model = os.getenv("EMBEDDINGS_MODEL", "bge-m3").strip()
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        self.puerto = int(os.getenv("PUERTO", "8001"))

settings = Settings()
