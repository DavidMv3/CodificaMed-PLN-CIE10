"""Subconjunto DIDÁCTICO de 22 códigos CIE-10 (estructura OMS), no un catálogo oficial completo.

Las etiquetas en español y los sinónimos son de trabajo; verificar código,
exclusiones, subcategoría y edición aplicable antes de cualquier uso real.
Fuente para consulta manual: https://icd.who.int/browse10/2019/en/
No utilizar para diagnósticos de personas reales.
"""
from __future__ import annotations

import re

CATALOGO: dict[str, str] = {
    "I10": "Hipertensión esencial (primaria)",
    "E11.9": "Diabetes mellitus tipo 2 sin complicaciones",
    "J18.9": "Neumonía, organismo no especificado",
    "R51": "Cefalea",
    "J06.9": "Infección aguda de las vías respiratorias superiores, no especificada",
    "J45.9": "Asma, no especificada",
    "J20.9": "Bronquitis aguda, no especificada",
    "K21.9": "Enfermedad por reflujo gastroesofágico sin esofagitis",
    "K29.7": "Gastritis, no especificada",
    "M54.5": "Lumbago / dolor lumbar",
    "N39.0": "Infección de vías urinarias, sitio no especificado",
    "R50.9": "Fiebre, no especificada",
    "R10.9": "Dolor abdominal, no especificado",
    "R05": "Tos",
    "G43.9": "Migraña, no especificada",
    "F41.9": "Trastorno de ansiedad, no especificado",
    "D64.9": "Anemia, no especificada",
    "E03.9": "Hipotiroidismo, no especificado",
    "E78.5": "Hiperlipidemia, no especificada",
    "K59.0": "Estreñimiento",
    "L30.9": "Dermatitis, no especificada",
    "H10.9": "Conjuntivitis, no especificada",
}

# Patrones para localizar menciones textuales (NER por reglas).
# Estas menciones NO prueban que el código específico sea clínicamente correcto.
_PATRONES: dict[str, str] = {
    "I10": r"\b(?:HTA|hipertensi[oó]n(?:\s+arterial)?)\b",
    "E11.9": r"\b(?:DM\s*2|diabetes(?:\s+mellitus)?\s+(?:tipo\s*)?2)\b",
    "J18.9": r"\bneumon[ií]a\b",
    "R51": r"\b(?:cefalea|dolor\s+de\s+cabeza)\b",
    "J06.9": r"\b(?:infecci[oó]n\s+(?:aguda\s+)?(?:de\s+)?v[ií]as\s+respiratorias\s+superiores|infecci[oó]n\s+respiratoria\s+aguda\s+alta)\b",
    "J45.9": r"\basma\b",
    "J20.9": r"\bbronquitis\s+aguda\b",
    "K21.9": r"\b(?:reflujo\s+gastroesof[aá]gico|ERGE)\b",
    "K29.7": r"\bgastritis\b",
    "M54.5": r"\b(?:lumbalgia|dolor\s+lumbar)\b",
    "N39.0": r"\b(?:infecci[oó]n\s+(?:de\s+)?(?:v[ií]as\s+)?urinaria(?:s)?|infecci[oó]n\s+de\s+v[ií]as\s+urinarias|ITU|IVU)\b",
    "R50.9": r"\bfiebre\b",
    "R10.9": r"\bdolor\s+abdominal\b",
    "R05": r"\btos\b",
    "G43.9": r"\bmigra[nñ]a\b",
    "F41.9": r"\btrastorno\s+de\s+ansiedad\b",
    "D64.9": r"\banemia\b",
    "E03.9": r"\bhipotiroidismo\b",
    "E78.5": r"\b(?:hiperlipidemia|dislipidemia)\b",
    "K59.0": r"\b(?:estre[nñ]imiento|constipaci[oó]n)\b",
    "L30.9": r"\bdermatitis\b",
    "H10.9": r"\bconjuntivitis\b",
}

assert set(_PATRONES) == set(CATALOGO), "Cada código debe tener un patrón"
ENTIDADES: dict[str, re.Pattern[str]] = {codigo: re.compile(patron, re.I) for codigo, patron in _PATRONES.items()}
