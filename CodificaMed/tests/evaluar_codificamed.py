"""Evaluación reproducible de CodificaMed con 20 notas clínicas FICTICIAS.

Ejemplos:
    python tests/evaluar_codificamed.py --modo reglas
    python tests/evaluar_codificamed.py --modo api --proveedor ollama --limite 5
    python tests/evaluar_codificamed.py --modo api --proveedor claude --limite 5

El modo reglas NO prueba el LLM. El modo api sí llama al endpoint real.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parents[1]
CASOS = Path(__file__).with_name("casos_ficticios.json")
ESTADOS = {"confirmado", "negado", "descartado", "incierto"}


def conjunto(hallazgos: list[dict]) -> set[tuple[str, str]]:
    return {(str(x.get("codigo", "")).strip().upper(), str(x.get("estado", "")).strip().lower())
            for x in hallazgos if x.get("codigo") and x.get("estado") in ESTADOS}


def prediccion_reglas(nota: str) -> tuple[list[dict], str]:
    # No necesita Ollama, pero requiere las dependencias del proyecto ya instaladas.
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    from app.codificamed import extraer_indicios
    return extraer_indicios(nota), "reglas_sin_llm"


def prediccion_api(nota: str, url: str, proveedor: str, motor: str, timeout: int) -> tuple[list[dict], str]:
    destino = url.rstrip("/") + "/api/codificamed/analizar"
    body = json.dumps({"nota": nota, "proveedor": proveedor, "motor": motor}, ensure_ascii=False).encode("utf-8")
    req = Request(destino, body, {"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            datos = json.load(resp)
    except HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="replace")[:450]
        raise RuntimeError(f"HTTP {exc.code}: {detalle}") from exc
    except URLError as exc:
        raise RuntimeError(f"No se pudo conectar a {destino}: {exc}") from exc
    hallazgos = [*datos.get("sugeridos", []), *datos.get("no_sugeridos", [])]
    return hallazgos, str(datos.get("modelo", proveedor))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modo", choices=["reglas", "api"], default="reglas", help="Reglas sin LLM o API completa con LLM")
    p.add_argument("--proveedor", choices=["ollama", "claude", "gemini"], default="ollama")
    p.add_argument("--motor", choices=["hibrido", "solo_llm", "solo_reglas"], default="hibrido",
                   help="En modo api: evaluar el sistema híbrido, solo el LLM o solo las reglas")
    p.add_argument("--url", default="http://localhost:8001")
    p.add_argument("--limite", type=int, default=0, help="Número de casos: 0 = todos")
    p.add_argument("--timeout", type=int, default=900, help="Segundos permitidos por cada caso")
    p.add_argument("--salida", default="", help="Ruta del JSON de salida (por defecto, resultados/evaluacion_*.json)")
    args = p.parse_args()
    if args.limite < 0:
        p.error("--limite no puede ser negativo")
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    if args.limite:
        casos = casos[:args.limite]

    tp = fp = fn = 0
    duracion_total = 0.0
    errores = 0
    registros: list[dict] = []
    modelo_observado = "reglas_sin_llm"
    print(f"Evaluando {len(casos)} casos ficticios en modo {args.modo}.\n")
    for indice, caso in enumerate(casos, 1):
        gold = conjunto(caso["esperados"])
        inicio = time.perf_counter()
        try:
            if args.modo == "reglas":
                hallazgos, modelo_observado = prediccion_reglas(caso["nota"])
            else:
                hallazgos, modelo_observado = prediccion_api(caso["nota"], args.url, args.proveedor, args.motor, args.timeout)
            pred = conjunto(hallazgos)
            segundos = round(time.perf_counter() - inicio, 3)
            duracion_total += segundos
            correctos = sorted(gold & pred)
            sobrantes = sorted(pred - gold)
            faltantes = sorted(gold - pred)
            tp += len(correctos)
            fp += len(sobrantes)
            fn += len(faltantes)
            estado = "OK" if pred == gold else "REVISAR"
            registros.append({"id": caso["id"], "nota_ficticia": caso["nota"], "esperados": sorted(gold),
                              "obtenidos": sorted(pred), "aciertos": correctos, "falsos_positivos": sobrantes,
                              "falsos_negativos": faltantes, "duracion_segundos": segundos})
            print(f"{indice:02}/{len(casos)}  {caso['id']} {estado:<7} {segundos:>7.2f} s | TP={len(correctos)} FP={len(sobrantes)} FN={len(faltantes)}", flush=True)
        except Exception as exc:
            errores += 1
            segundos = round(time.perf_counter() - inicio, 3)
            registros.append({"id": caso["id"], "error": str(exc), "duracion_segundos": segundos})
            print(f"{indice:02}/{len(casos)}  {caso['id']} ERROR  {exc}", flush=True)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    completados = len(casos) - errores
    informe = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "tipo": "micro-promedio por par (codigo_CIE10, estado) y por caso; etiquetas sintéticas académicas",
        "modo": args.modo,
        "motor": args.motor if args.modo == "api" else "solo_reglas",
        "proveedor_solicitado": args.proveedor if args.modo == "api" else None,
        "modelo_observado": modelo_observado,
        "total_casos": len(casos),
        "casos_completados": completados,
        "casos_fallidos": errores,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "duracion_acumulada_segundos": round(duracion_total, 2),
        "nota_metodologica": ("Se excluyen los casos con error técnico del cálculo; no representan predicciones negativas. "
                             "Comparar modelos usando idénticos casos y parámetros. No hay validación clínica ni corpus real."),
        "casos": registros,
    }
    nombre = ("evaluacion_reglas.json" if args.modo == "reglas"
              else f"evaluacion_{args.proveedor}_{args.motor}.json")
    destino = Path(args.salida) if args.salida else RAIZ / "resultados" / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nCasos procesados: {completados}/{len(casos)}; errores: {errores}")
    print(f"TP={tp}  FP={fp}  FN={fn} | PRECISIÓN={precision:.2%}  RECALL={recall:.2%}  F1={f1:.2%}")
    print(f"Resultado guardado en: {destino}")
    if errores:
        print("ATENCIÓN: Hay casos sin procesar; no interpretes estas métricas como evaluación completa.")
    return 0 if not errores else 2


if __name__ == "__main__":
    raise SystemExit(main())
