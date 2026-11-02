"""Pruebas de humo sobre menciones ficticias del catálogo extendido, SIN LLM.

Desde CodificaMed: .\\.venv\\Scripts\\python.exe tests\\probar_catalogo_paso5.py
"""
from __future__ import annotations
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from app.codificamed import CATALOGO, extraer_indicios  # noqa: E402

PRUEBAS = [
    ("Paciente con asma. Niega fiebre.", {("J45.9", "confirmado"), ("R50.9", "negado")}),
    ("Se descarta infección urinaria. Tiene lumbalgia.", {("N39.0", "descartado"), ("M54.5", "confirmado")}),
    ("Hipotiroidismo estable. Posible anemia.", {("E03.9", "confirmado"), ("D64.9", "incierto")}),
    ("Dolor abdominal y tos. Sin neumonía.", {("R10.9", "confirmado"), ("R05", "confirmado"), ("J18.9", "negado")}),
    ("Paciente con HTA controlada. DM2 en estudio.", {("I10", "confirmado"), ("E11.9", "incierto")}),
]

def main() -> int:
    errores = 0
    print(f"Catálogo cargado: {len(CATALOGO)} códigos. Pruebas de humo: {len(PRUEBAS)}")
    for i, (nota, esperado) in enumerate(PRUEBAS, 1):
        obtenido = {(h["codigo"], h["estado"]) for h in extraer_indicios(nota)}
        correcto = obtenido == esperado
        errores += not correcto
        print(f"{i:02d}: {'OK' if correcto else 'REVISAR'} | esperado={sorted(esperado)} | obtenido={sorted(obtenido)}")
    print(f"Pruebas sin diferencias: {len(PRUEBAS)-errores}/{len(PRUEBAS)}")
    return 1 if errores else 0

if __name__ == "__main__":
    raise SystemExit(main())
