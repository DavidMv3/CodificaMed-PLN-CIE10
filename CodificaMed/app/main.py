"""API educativa de CodificaMed: notas clínicas ficticias y clasificación CIE-10."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .codificamed import router as codificamed_router

app = FastAPI(
    title="CodificaMed",
    description="Prototipo académico de procesamiento de lenguaje natural (PLN) y CIE-10.",
    version="1.0.0",
)
app.include_router(codificamed_router)
HTML = Path(__file__).resolve().parent / "static" / "codificamed.html"

@app.get("/", include_in_schema=False)
def inicio() -> FileResponse:
    return FileResponse(HTML)

@app.get("/api/salud", tags=["Sistema"])
def salud() -> dict:
    return {"aplicacion": "CodificaMed", "estado": "operativo", "uso": "solo educativo"}
