"""CodificaMed académico: catálogo de prueba, LLM y control verificable de negaciones.

No debe utilizarse para diagnósticos, codificación real ni datos de pacientes.
"""
from __future__ import annotations

import re
import time
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .llm import ErrorLLM, obtener_proveedor


from .catalogo_cie10 import CATALOGO, ENTIDADES

router = APIRouter(prefix="/api/codificamed", tags=["CodificaMed"])

DESCARTE = re.compile(r"\b(?:se\s+)?descart(?:a|an|ó|ado|ada|ados|adas|aron|aba)\b", re.I)
NEGACION = re.compile(r"\b(?:niega(?:n)?|sin|no\s+(?:presenta|refiere|hay|evidencia|se\s+evidencia))\b", re.I)
DUDA = re.compile(r"\b(?:sospecha(?:\s+de)?|posible|probable|no\s+se\s+descarta)\b", re.I)
NO_DESCARTA = re.compile(r"\bno\s+se\s+descarta\b", re.I)
EN_ESTUDIO = re.compile(r"\s*(?:en\s+estudio|sin\s+confirmaci[oó]n|pendiente\s+de\s+confirmaci[oó]n)\b", re.I)
ESTADOS = {"confirmado", "negado", "descartado", "incierto"}


class Entrada(BaseModel):
    nota: str = Field(min_length=10, max_length=5000)
    proveedor: Literal["ollama", "claude", "gemini"] = "ollama"
    motor: Literal["hibrido", "solo_llm", "solo_reglas"] = "hibrido"


ESQUEMA = {
    "type": "object",
    "properties": {
        "hallazgos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "codigo": {"type": "string", "enum": list(CATALOGO)},
                    "evidencia": {"type": "string"},
                    "estado": {"type": "string", "enum": sorted(ESTADOS)},
                },
                "required": ["codigo", "evidencia", "estado"],
            },
        }
    },
    "required": ["hallazgos"],
}


def _evaluar_contexto(nota: str, inicio: int, fin: int) -> tuple[str, str]:
    """Determina un estado por señales próximas y devuelve evidencia textual breve.

    Para prototipo académico: no sustituye a un detector de negaciones clínico.
    """
    corte = max(nota.rfind(x, 0, inicio) for x in (".", ";", "\n", "!", "?"))
    tramo = nota[corte + 1:inicio]
    # La expresión "no se descarta" significa incertidumbre, no descarte.
    # Detectarla como unidad evita interpretar solo la palabra "descarta".
    coincidencias_no_descarta = list(NO_DESCARTA.finditer(tramo))
    if coincidencias_no_descarta:
        ultimo = coincidencias_no_descarta[-1]
        if len(tramo) - ultimo.end() <= 55:
            return "incierto", nota[corte + 1 + ultimo.start():fin].strip()

    indicadores: list[tuple[int, str]] = []
    for patron, estado in ((DESCARTE, "descartado"), (NEGACION, "negado"), (DUDA, "incierto")):
        for coincidencia in patron.finditer(tramo):
            # Evita propagar una negación demasiado lejana a otro diagnóstico.
            if len(tramo) - coincidencia.end() <= 55:
                indicadores.append((coincidencia.start(), estado))

    if indicadores:
        posicion, estado = max(indicadores, key=lambda x: x[0])
        evidencia = nota[corte + 1 + posicion:fin].strip()
        # "no se descarta" expresa incertidumbre, NO un descarte confirmado.
        if re.search(r"\bno\s+se\s+descarta\b", evidencia, re.I):
            estado = "incierto"
        return estado, evidencia

    # Contempla calificadores DESPUÉS de la entidad.
    cola = nota[fin:fin + 65]
    tras = re.match(r"\s+(descartad[ao]s?|negad[ao]s?)\b", cola, re.I)
    if tras:
        estado = "descartado" if tras.group(1).lower().startswith("descart") else "negado"
        return estado, nota[inicio:fin + tras.end()].strip()
    estudio = EN_ESTUDIO.match(cola)
    if estudio:
        evidencia = nota[inicio:fin + estudio.end()].strip()
        # Conservar la continuación "sin confirmación" si forma parte del mismo tramo.
        extra = re.match(r"\s*,?\s*sin\s+confirmaci[oó]n\b", nota[fin + estudio.end():], re.I)
        if extra:
            evidencia = nota[inicio:fin + estudio.end() + extra.end()].strip()
        return "incierto", evidencia

    return "confirmado", nota[inicio:fin]


def extraer_indicios(nota: str) -> list[dict]:
    """Análisis de respaldo verificable con entidades y negación por contexto."""
    hallazgos = []
    for codigo, patron in ENTIDADES.items():
        for coincidencia in patron.finditer(nota):
            estado, evidencia = _evaluar_contexto(nota, coincidencia.start(), coincidencia.end())
            hallazgos.append({
                "codigo": codigo,
                "descripcion": CATALOGO[codigo],
                "evidencia": evidencia,
                "estado": estado,
            })
    return hallazgos


def _filtrar_respuesta_llm(nota: str, prediccion: dict) -> list[dict]:
    """Conservar únicamente códigos y evidencias literales de la nota.

    Importante: NO sustituir aquí el estado por la regla, para que la
    evaluación `solo_llm` mida de verdad al modelo seleccionado.
    """
    salida: list[dict] = []
    claves: set[tuple[str, str, str]] = set()
    if not isinstance(prediccion, dict):
        return salida
    hallazgos = prediccion.get("hallazgos", [])
    if not isinstance(hallazgos, list):
        return salida
    for h in hallazgos:
        if not isinstance(h, dict):
            continue
        codigo = str(h.get("codigo", "")).strip()
        evidencia = str(h.get("evidencia", "")).strip()
        estado = str(h.get("estado", "")).strip().lower()
        if codigo not in CATALOGO or estado not in ESTADOS or not evidencia:
            continue
        # No aceptar frases inventadas ni códigos cuya entidad no aparece en la evidencia.
        if evidencia.casefold() not in nota.casefold() or not ENTIDADES[codigo].search(evidencia):
            continue
        clave = (codigo, estado, evidencia.casefold())
        if clave not in claves:
            claves.add(clave)
            salida.append({"codigo": codigo, "descripcion": CATALOGO[codigo],
                           "evidencia": evidencia, "estado": estado})
    return salida


@router.post("/analizar")
def analizar(entrada: Entrada) -> dict:
    reglas = extraer_indicios(entrada.nota)
    modelo_nombre = "reglas_sin_llm"
    hallazgos_llm: list[dict] = []
    if entrada.motor != "solo_reglas":
        modelo = obtener_proveedor(entrada.proveedor)
        modelo_nombre = modelo.modelo
        sistema = (
            "Eres un asistente académico de codificación CIE-10 sobre notas FICTICIAS. "
            "Identifica únicamente los códigos del catálogo dado. "
            "Separa presente, negado, descartado e incierto. "
            "Usa 'incierto' para sospecha, posibilidad, 'no se descarta', "
            "'en estudio' y 'sin confirmación'. "
            "La evidencia debe ser una frase LITERAL de la nota; no inventes datos. "
            "Si un código no aparece en la nota, NO lo incluyas."
            "\nREGLAS IMPORTANTES DE CLASIFICACION:\n"
            "1. CONFIRMADO: enfermedad presente o diagnosticada, "
            "aunque este controlada, estable o en tratamiento.\n"
            "2. NEGADO: el texto niega explicitamente su presencia.\n"
            "3. DESCARTADO: existe una exclusion explicita, "
            "como 'se descarta neumonia'.\n"
            "4. INCIERTO: sospecha, posible diagnostico, "
            "en estudio o sin confirmacion.\n"
            "5. La palabra 'controlada' NUNCA significa descartada.\n"
            "6. No inventes negaciones ni descartes.\n"
            "EJEMPLO: 'Paciente con HTA controlada.' "
            "=> codigo I10, estado confirmado.\n"
        )
        catalogo_texto = "\n".join(f"{k}: {v}" for k, v in CATALOGO.items())
        prompt = (
            f"Catálogo permitido:\n{catalogo_texto}\n\n"
            f"Nota clínica ficticia:\n{entrada.nota}\n\n"
            "Devuelve todos los hallazgos relevantes del catálogo, incluyendo los negados "
            "y descartados. Cada hallazgo debe tener código, estado y evidencia exacta de la nota."
            "\nREGLAS DE SALIDA:\n"
            "Incluye SOLO los diagnosticos mencionados en la nota.\n"
            "No enumeres todos los codigos del catalogo.\n"
            "No marques como descartadas enfermedades ausentes.\n"
            "Devuelve una entrada por diagnostico mencionado.\n"
            "La evidencia debe aparecer literalmente en la nota.\n"
            "Si no identificas diagnosticos, devuelve "
            '{"hallazgos": []}.\n'
        )
        try:
            inicio_llm = time.perf_counter()
            prediccion = modelo.generar_json(
                sistema, prompt, ESQUEMA, "codificar_nota"
            )

            duracion_llm = time.perf_counter() - inicio_llm
            print(f"Tiempo de generación LLM: {duracion_llm:.2f} s", flush=True)
        except ErrorLLM as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        hallazgos_llm = _filtrar_respuesta_llm(entrada.nota, prediccion)

    if entrada.motor == "solo_reglas":
        hallazgos = reglas
    elif entrada.motor == "solo_llm":
        hallazgos = hallazgos_llm
    else:
        # Modo híbrido: las reglas ancladas al texto tienen preferencia para
        # los códigos reconocidos. El LLM agrega solo los no vistos.
        hallazgos = list(reglas)
        existentes = {h["codigo"] for h in hallazgos}
        for h in hallazgos_llm:
            if h["codigo"] not in existentes:
                hallazgos.append(h)
                existentes.add(h["codigo"])

    return {
        "modelo": modelo_nombre,
        "motor": entrada.motor,
        "sugeridos": [h for h in hallazgos if h["estado"] == "confirmado"],
        "no_sugeridos": [h for h in hallazgos if h["estado"] != "confirmado"],
        "aviso": "Prototipo académico de catálogo seleccionado de 22 códigos; verificar con versión oficial de CIE-10 y revisión humana. No utilizar con pacientes reales.",
    }
