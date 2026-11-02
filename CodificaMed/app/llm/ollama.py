"""Proveedor local: Ollama (https://ollama.com).

Usa la API REST de Ollama en http://localhost:11434.
- /api/chat con "format" = JSON Schema -> salida estructurada garantizada
  (Ollama restringe la generación del modelo a una gramática derivada del esquema).
- /api/embed -> vectores para la búsqueda semántica.
"""
from __future__ import annotations

import json

import httpx

from ..config import settings
from .base import ErrorConexionLLM, ErrorLLM, ProveedorLLM, extraer_json

# Modelos que "piensan" antes de responder; se les desactiva para ahorrar tiempo.
_MODELOS_CON_RAZONAMIENTO = ("qwen3", "deepseek-r1", "gpt-oss", "magistral")


class ProveedorOllama(ProveedorLLM):
    nombre = "ollama"

    def __init__(self) -> None:
        self.host = settings.ollama_host
        self.modelo = settings.ollama_model
        self.modelo_embeddings = settings.embeddings_model

    # ---------------------------------------------------------------- chat
    def _chat(self, sistema: str, prompt: str, formato: dict | None) -> str:
        cuerpo: dict = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,  # baja: queremos extracción fiel, no creatividad
                "num_ctx": settings.ollama_num_ctx,
            },
            "keep_alive": "30m",
        }
        if formato is not None:
            cuerpo["format"] = formato
        if any(m in self.modelo.lower() for m in _MODELOS_CON_RAZONAMIENTO):
            cuerpo["think"] = False
        try:
            r = httpx.post(f"{self.host}/api/chat", json=cuerpo, timeout=settings.ollama_timeout)
        except httpx.ConnectError as e:
            raise ErrorConexionLLM("No se pudo conectar con Ollama. ¿Está abierto? (ollama serve)") from e
        except httpx.TimeoutException as e:
            raise ErrorLLM("Ollama tardó demasiado en responder.") from e
        if r.status_code == 404:
            raise ErrorConexionLLM(f"El modelo '{self.modelo}' no está descargado. Ejecuta: ollama pull {self.modelo}")
        if r.status_code >= 400:
            raise ErrorLLM(f"Ollama respondió {r.status_code}: {r.text[:300]}")
        return r.json().get("message", {}).get("content", "")

    def generar_json(self, sistema: str, prompt: str, schema: dict, nombre: str) -> dict:
        sistema_json = (
            f"{sistema}\n\nResponde ÚNICAMENTE con un objeto JSON válido que cumpla este esquema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        ultimo_error: Exception | None = None
        for _ in range(2):  # un reintento si el JSON llega mal formado
            try:
                return extraer_json(self._chat(sistema_json, prompt, schema))
            except ErrorConexionLLM:
                raise
            except ErrorLLM as e:
                ultimo_error = e
        raise ultimo_error or ErrorLLM("Error desconocido")

    def generar_texto(self, sistema: str, prompt: str) -> str:
        return self._chat(sistema, prompt, None).strip()

    # ----------------------------------------------------------- embeddings
    def embeddings(self, textos: list[str]) -> list[list[float]] | None:
        vectores: list[list[float]] = []
        try:
            for i in range(0, len(textos), 32):
                r = httpx.post(
                    f"{self.host}/api/embed",
                    json={"model": self.modelo_embeddings, "input": textos[i : i + 32]},
                    timeout=settings.ollama_timeout,
                )
                if r.status_code >= 400:
                    return None
                vectores.extend(r.json().get("embeddings", []))
        except httpx.HTTPError:
            return None
        return vectores if len(vectores) == len(textos) else None

    # --------------------------------------------------------------- estado
    def estado(self) -> dict:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=3)
            instalados = [m["name"] for m in r.json().get("models", [])]
        except (httpx.HTTPError, ValueError, KeyError):
            return {
                "disponible": False,
                "modelo": self.modelo,
                "mensaje": "Ollama no está en ejecución",
                "instalados": [],
            }

        def presente(nombre: str) -> bool:
            base = nombre if ":" in nombre else f"{nombre}:latest"
            return any(m == nombre or m == base for m in instalados)

        modelo_ok = presente(self.modelo)
        emb_ok = presente(self.modelo_embeddings)
        mensaje = "Listo" if modelo_ok else f"Falta descargar: ollama pull {self.modelo}"
        if modelo_ok and not emb_ok and settings.embeddings_provider == "ollama":
            mensaje = f"Listo (sin embeddings: ollama pull {self.modelo_embeddings})"
        return {
            "disponible": modelo_ok,
            "modelo": self.modelo,
            "modelo_embeddings": self.modelo_embeddings,
            "embeddings_disponibles": emb_ok,
            "mensaje": mensaje,
            "instalados": instalados,
        }
