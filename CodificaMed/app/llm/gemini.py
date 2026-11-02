"""Gemini API para CodificaMed (nivel gratuito sujeto a cuota por proyecto).

Utiliza el cliente HTTPX que ya requiere AplicaTI/CodificaMed; no necesita
instalar un SDK adicional. NO enviar datos clinicos reales a la API externa.
"""
from __future__ import annotations

import httpx

from ..config import settings
from .base import ErrorConexionLLM, ErrorLLM, ProveedorLLM, extraer_json


class ProveedorGemini(ProveedorLLM):
    nombre = "gemini"

    def __init__(self) -> None:
        self.modelo = settings.gemini_model

    def _solicitar(self, sistema: str, prompt: str, esquema: dict | None = None) -> str:
        if not settings.gemini_api_key:
            raise ErrorConexionLLM("Falta GEMINI_API_KEY en CodificaMed/.env")

        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + self.modelo + ":generateContent"
        )
        config: dict = {"maxOutputTokens": 1600, "temperature": 0}
        if esquema is not None:
            config["responseMimeType"] = "application/json"
            config["responseSchema"] = esquema

        datos = {
            "systemInstruction": {"parts": [{"text": sistema}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config,
        }
        try:
            # Una llamada por analisis; NO reintentamos automaticamente las cuotas 429.
            with httpx.Client(timeout=120.0) as cliente:
                resp = cliente.post(
                    endpoint,
                    headers={
                        "x-goog-api-key": settings.gemini_api_key,
                        "Content-Type": "application/json",
                    },
                    json=datos,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ErrorConexionLLM("Gemini no respondió a tiempo o hay un problema de red.") from exc

        if resp.status_code in (400, 401, 403):
            # No se incluyen detalles de servidor que accidentalmente pudieran contener datos.
            raise ErrorConexionLLM(
                f"Gemini devolvió HTTP {resp.status_code}. Revisa la clave, "
                "el modelo, la elegibilidad del nivel gratuito y el proyecto en AI Studio."
            )
        if resp.status_code == 429:
            raise ErrorLLM(
                "Gemini devolvió HTTP 429: límite gratuito agotado "
                "(solicitudes o tokens). Revisa tus cuotas en Google AI Studio."
            )
        if resp.status_code >= 400:
            raise ErrorLLM(f"Gemini devolvió HTTP {resp.status_code}.")
        try:
            salida = resp.json()
            partes = salida["candidates"][0]["content"]["parts"]
            texto = "".join(p.get("text", "") for p in partes if isinstance(p, dict))
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ErrorLLM("Gemini no devolvió una respuesta de texto válida.") from exc
        if not texto.strip():
            raise ErrorLLM("Gemini devolvió una respuesta vacía.")
        return texto

    def generar_json(self, sistema: str, prompt: str, schema: dict, nombre: str) -> dict:
        texto = self._solicitar(sistema, prompt, esquema=schema)
        return extraer_json(texto)

    def generar_texto(self, sistema: str, prompt: str) -> str:
        return self._solicitar(sistema, prompt)

    def estado(self) -> dict:
        configurado = bool(settings.gemini_api_key)
        return {
            "disponible": configurado,
            "modelo": self.modelo,
            "mensaje": "API key configurada" if configurado else "Falta GEMINI_API_KEY en .env",
        }
