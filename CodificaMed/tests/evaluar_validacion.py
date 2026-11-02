"""Evaluacion de CodificaMed sobre un conjunto NUEVO de notas FICTICIAS.

Conserva intacto tests/evaluar_codificamed.py y los archivos JSON anteriores.
Ejecutar desde la raiz de CodificaMed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Reutiliza los metodos de medicion ya existentes en el proyecto.
from evaluar_codificamed import conjunto, prediccion_reglas, prediccion_api

RAIZ = Path(__file__).resolve().parents[1]
CASOS_NUEVOS = Path(__file__).with_name("casos_validacion_22.json")
CODIGOS_CATALOGO = {
    "I10", "E11.9", "J18.9", "R51", "J06.9", "J45.9", "J20.9", "K21.9",
    "K29.7", "M54.5", "N39.0", "R50.9", "R10.9", "R05", "G43.9", "F41.9",
    "D64.9", "E03.9", "E78.5", "K59.0", "L30.9", "H10.9"
}
ESTADOS = {"confirmado", "negado", "descartado", "incierto"}


def leer_casos() -> list[dict]:
    datos = json.loads(CASOS_NUEVOS.read_text(encoding="utf-8"))
    if not isinstance(datos, list) or not datos:
        raise ValueError("El archivo de validacion debe contener una lista no vacia")
    ids = [x.get("id") for x in datos]
    if len(set(ids)) != len(ids):
        raise ValueError("Hay IDs de casos repetidos")
    for item in datos:
        if not isinstance(item.get("nota"), str) or len(item["nota"]) < 10:
            raise ValueError(f"Nota invalida: {item.get('id')}")
        for h in item.get("esperados", []):
            if h.get("codigo") not in CODIGOS_CATALOGO or h.get("estado") not in ESTADOS:
                raise ValueError(f"Etiqueta invalida: {item.get('id')}: {h}")
    cobertura = {e["codigo"] for x in datos for e in x["esperados"]}
    faltantes = CODIGOS_CATALOGO - cobertura
    if faltantes:
        raise ValueError(f"Catalogo sin cobertura: {sorted(faltantes)}")
    return datos


def main() -> int:
    p = argparse.ArgumentParser(description="Validacion con 40 notas nuevas y 22 codigos CIE-10 didacticos")
    p.add_argument("--modo", choices=["reglas", "api"], default="reglas")
    p.add_argument("--proveedor", choices=["ollama", "claude", "gemini"], default="ollama")
    p.add_argument("--motor", choices=["hibrido", "solo_llm", "solo_reglas"], default="hibrido")
    p.add_argument("--limite", type=int, default=0, help="0=40 casos; por ejemplo 5 para prueba inicial")
    p.add_argument("--url", default="http://localhost:8001")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--salida", default="")
    args = p.parse_args()
    if args.limite < 0:
        p.error("--limite no puede ser negativo")
    casos = leer_casos()
    if args.limite:
        casos = casos[:args.limite]
    tp = fp = fn = errores = 0
    registros = []
    duracion_total = 0.0
    modelo_observado = "reglas_sin_llm"
    print(f"Validando {len(casos)} casos NUEVOS; modo={args.modo}, motor={args.motor}, proveedor={args.proveedor}.", flush=True)
    for i, caso in enumerate(casos, 1):
        gold = conjunto(caso["esperados"])
        t0 = time.perf_counter()
        try:
            if args.modo == "reglas":
                hallazgos, modelo_observado = prediccion_reglas(caso["nota"])
            else:
                hallazgos, modelo_observado = prediccion_api(caso["nota"], args.url, args.proveedor, args.motor, args.timeout)
            pred = conjunto(hallazgos)
            correctos = sorted(gold & pred)
            sobrantes = sorted(pred - gold)
            faltantes = sorted(gold - pred)
            tp += len(correctos)
            fp += len(sobrantes)
            fn += len(faltantes)
            segundos = round(time.perf_counter() - t0, 3)
            duracion_total += segundos
            estado = "OK" if gold == pred else "REVISAR"
            registros.append({"id": caso["id"], "nota_ficticia": caso["nota"], "esperados": sorted(gold),
                               "obtenidos": sorted(pred), "aciertos": correctos,
                               "falsos_positivos": sobrantes, "falsos_negativos": faltantes,
                               "duracion_segundos": segundos})
            print(f"{i:02}/{len(casos)}  {caso['id']} {estado:<7} {segundos:>7.2f} s | TP={len(correctos)} FP={len(sobrantes)} FN={len(faltantes)}", flush=True)
        except Exception as exc:
            errores += 1
            segundos = round(time.perf_counter() - t0, 3)
            duracion_total += segundos
            registros.append({"id": caso["id"], "error": str(exc), "duracion_segundos": segundos})
            print(f"{i:02}/{len(casos)}  {caso['id']} ERROR: {exc}", flush=True)
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0
    informe = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "tipo": "Validacion academica de notas sinteticas nuevas, micro promedio por par (codigo, estado)",
        "fuente_casos": str(CASOS_NUEVOS.relative_to(RAIZ)),
        "modo": args.modo,
        "motor": args.motor if args.modo == "api" else "solo_reglas",
        "proveedor": args.proveedor if args.modo == "api" else None,
        "modelo_observado": modelo_observado,
        "total_casos": len(casos), "casos_completados": len(casos)-errores, "casos_fallidos": errores,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
        "duracion_acumulada_segundos": round(duracion_total, 3),
        "nota_metodologica": "Etiquetas creadas con notas ficticias, sin validacion clinica externa. No usar para toma de decisiones medicas. La cobertura se limita a 22 codigos.",
        "casos": registros,
    }
    nombre = "validacion_reglas_22.json" if args.modo == "reglas" else f"validacion_{args.proveedor}_{args.motor}_22.json"
    destino = Path(args.salida) if args.salida else RAIZ/"resultados"/nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(informe,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    print(f"\nCasos procesados: {len(casos)-errores}/{len(casos)}; errores: {errores}")
    print(f"TP={tp} FP={fp} FN={fn} | PRECISION={precision:.2%} RECALL={recall:.2%} F1={f1:.2%}")
    print(f"Resultado guardado en: {destino}")
    if errores:
        print("IMPORTANTE: Las metricas excluyen los casos con error. No reportar como validacion completa.")
    return 2 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
