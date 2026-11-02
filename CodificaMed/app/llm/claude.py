"""Proveedor en la nube: Claude (API de Anthropic).

La salida estructurada se obtiene "forzando" una herramienta cuyo
input_schema es el esquema JSON que queremos: el modelo está obligado a
llamar a esa herramienta y sus argumentos son nuestro JSON.
No se envía "temperature": las versiones recientes del SDK de Anthropic ya no
lo aceptan en messages.create.
Anthropic no ofrece embeddings: la búsqueda semántica sigue usando el
modelo local de Ollama (o BM25 si Ollama no está disponible).
"""
from __future__ import annotations

from ..config import settings
from .base import ErrorConexionLLM, ErrorLLM, ProveedorLLM, extraer_json


class ProveedorClaude(ProveedorLLM):
    nombre = "claude"

    def __init__(self) -> None:
        self.modelo = settings.claude_model
        self._cliente = None

    def _cliente_api(self):
        if not settings.anthropic_api_key:
            raise ErrorConexionLLM("Falta ANTHROPIC_API_KEY en el archivo .env")
        if self._cliente is None:
            import anthropic

            self._cliente = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=3)
        return self._cliente

    def _crear(self, **kwargs):
        import anthropic

        try:
            return self._cliente_api().messages.create(model=self.modelo, **kwargs)
        except anthropic.AuthenticationError as e:
            raise ErrorConexionLLM("La API key de Claude no es válida.") from e
        except anthropic.NotFoundError as e:
            raise ErrorConexionLLM(f"El modelo '{self.modelo}' no existe. Revisa CLAUDE_MODEL en .env") from e
        except anthropic.APIConnectionError as e:
            raise ErrorConexionLLM("Sin conexión con la API de Claude.") from e
        except anthropic.APIError as e:
            raise ErrorLLM(f"Error de la API de Claude: {e}") from e

    def generar_json(self, sistema: str, prompt: str, schema: dict, nombre: str) -> dict:
        respuesta = self._crear(
            max_tokens=8000,
            system=sistema,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": nombre,
                    "description": "Registra el resultado del análisis con la estructura indicada.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": nombre},
        )
        for bloque in respuesta.content:
            if bloque.type == "tool_use":
                return dict(bloque.input)
        # Respaldo: si por alguna razón respondió en texto
        texto = "".join(b.text for b in respuesta.content if b.type == "text")
        return extraer_json(texto)

    def generar_texto(self, sistema: str, prompt: str) -> str:
        respuesta = self._crear(
            max_tokens=2000,
            system=sistema,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in respuesta.content if b.type == "text").strip()

    def estado(self) -> dict:
        configurado = bool(settings.anthropic_api_key)
        return {
            "disponible": configurado,
            "modelo": self.modelo,
            "mensaje": "API key configurada" if configurado else "Falta ANTHROPIC_API_KEY en .env",
        }
