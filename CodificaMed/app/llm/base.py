"""Interfaz común para todos los proveedores de LLM.

El pipeline nunca habla directamente con Ollama ni con Claude: habla con
esta interfaz. Por eso cambiar de modelo es cambiar una variable.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


class ErrorLLM(Exception):
    """Error al comunicarse con el modelo o al interpretar su respuesta."""


class ErrorConexionLLM(ErrorLLM):
    """El proveedor no está disponible (apagado, sin API key, modelo inexistente).
    Detiene todo el análisis: no tiene sentido seguir con los demás módulos."""


class ProveedorLLM(ABC):
    nombre: str = "base"
    modelo: str = ""

    @abstractmethod
    def generar_json(self, sistema: str, prompt: str, schema: dict, nombre: str) -> dict:
        """Devuelve un dict que respeta (en lo posible) el JSON Schema dado."""

    @abstractmethod
    def generar_texto(self, sistema: str, prompt: str) -> str:
        """Respuesta libre en texto (se usa en el chat)."""

    def embeddings(self, textos: list[str]) -> list[list[float]] | None:
        """Vectores para búsqueda semántica. None si el proveedor no ofrece embeddings."""
        return None

    @abstractmethod
    def estado(self) -> dict:
        """Información para la interfaz: si está disponible y qué modelo usa."""


# ---------------------------------------------------------------------------
# Utilidades compartidas
# ---------------------------------------------------------------------------

def extraer_json(texto: str) -> dict:
    """Interpreta JSON aunque el modelo lo envuelva en ```json ... ``` o agregue texto."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        inicio, fin = texto.find("{"), texto.rfind("}")
        if inicio != -1 and fin > inicio:
            try:
                return json.loads(texto[inicio : fin + 1])
            except json.JSONDecodeError:
                pass
    raise ErrorLLM("El modelo no devolvió un JSON válido.")


def completar_con_schema(dato: Any, schema: dict) -> Any:
    """Rellena con valores vacíos lo que el modelo omitió, para que la
    interfaz nunca reciba campos faltantes (los modelos pequeños a veces omiten)."""
    tipo = schema.get("type")
    if tipo == "object":
        dato = dato if isinstance(dato, dict) else {}
        for clave, sub in schema.get("properties", {}).items():
            dato[clave] = completar_con_schema(dato.get(clave), sub)
        return dato
    if tipo == "array":
        if not isinstance(dato, list):
            return []
        return [completar_con_schema(x, schema.get("items", {})) for x in dato]
    if tipo == "string":
        if dato is None:
            return ""
        if "enum" in schema and str(dato) not in schema["enum"]:
            return schema["enum"][-1]
        return str(dato)
    if tipo in ("number", "integer"):
        try:
            return float(dato) if tipo == "number" else int(float(dato))
        except (TypeError, ValueError):
            return 0
    if tipo == "boolean":
        if isinstance(dato, bool):
            return dato
        return str(dato).strip().lower() in {"true", "si", "sí", "1", "yes"}
    return dato
