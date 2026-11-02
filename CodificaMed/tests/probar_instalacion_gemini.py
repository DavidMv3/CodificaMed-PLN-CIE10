"""Chequeo local que NO consume cuotas ni envía notas clínicas a Google."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.codificamed import Entrada
from app.llm import obtener_proveedor

p = obtener_proveedor("gemini")
assert p.modelo == settings.gemini_model
assert Entrada(nota="Paciente con asma diagnosticada.", proveedor="gemini").proveedor == "gemini"
assert Path("app/static/codificamed.html").read_text(encoding="utf-8").count('value="gemini"') >= 1
print("OK: proveedor Gemini registrado, entrada FastAPI valida y opcion web visible.")
print("Modelo:", p.modelo)
print("Clave configurada:", "SI" if settings.gemini_api_key else "NO (debes agregarla a .env)")
