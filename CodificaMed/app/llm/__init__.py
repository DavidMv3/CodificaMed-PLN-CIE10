"""Selector de LLM para CodificaMed."""
from __future__ import annotations
from ..config import settings
from .base import ErrorConexionLLM, ErrorLLM, ProveedorLLM
from .ollama import ProveedorOllama
from .claude import ProveedorClaude
from .gemini import ProveedorGemini

PROVEEDORES = {"ollama": ProveedorOllama, "claude": ProveedorClaude, "gemini": ProveedorGemini}

def obtener_proveedor(nombre: str | None = None) -> ProveedorLLM:
    nombre = (nombre or settings.llm_provider).lower()
    if nombre not in PROVEEDORES:
        raise ErrorLLM(f"Proveedor desconocido: {nombre}")
    return PROVEEDORES[nombre]()

__all__ = ["ErrorConexionLLM", "ErrorLLM", "ProveedorLLM", "obtener_proveedor", "PROVEEDORES"]
