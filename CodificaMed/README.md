# CodificaMed — Prototipo académico de PLN y CIE-10

**Base de Conocimiento | ESPOCH - FIE - Ingeniería de Software**

CodificaMed recibe una **nota clínica ficticia**, identifica menciones de diagnósticos o síntomas dentro de un **subconjunto académico de 22 códigos CIE-10**, diferencia estados `confirmado`, `negado`, `descartado` e `incierto` y presenta la frase de evidencia. Está destinado **solo a demostración y aprendizaje**: no debe utilizarse con información real de pacientes ni para diagnóstico, tratamiento o facturación.

## 1. Requisitos

- Windows 10/11 con Python **3.11** (también compatible con otros entornos Python modernos), internet para instalar dependencias y un navegador web.
- [Ollama](https://ollama.com/download) para análisis local con `qwen2.5:3b`.
- Opcional: clave de la API externa de Gemini creada en [Google AI Studio](https://aistudio.google.com/api-keys). Su nivel gratuito depende de cuotas, región y modelo. **No activar facturación sin intención de pagar**.
- Para el modo `solo_reglas`, no hace falta que Ollama o Gemini estén activos.

## 2. Instalación en Windows

Desde la carpeta `CodificaMed`:

```powershell
.\instalar.bat
ollama pull qwen2.5:3b
```

Abre `.env` (se genera desde `.env.example`) y deja, como mínimo:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_HOST=http://localhost:11434
OLLAMA_NUM_CTX=4096
OLLAMA_TIMEOUT=180
PUERTO=8001
```

Para usar la API externa añade **en tu archivo local `.env`**, nunca en el repositorio:

```dotenv
GEMINI_API_KEY=PEGA_TU_CLAVE_SOLO_EN_TU_EQUIPO
GEMINI_MODEL=gemini-3.5-flash-lite
```

El nombre del modelo externo se conserva de la evaluación realizada por el autor. Si Google cambia la disponibilidad, consulta en AI Studio los modelos habilitados y actualiza el identificador. Nunca compartas la clave.

Inicia el servidor con:

```powershell
.\iniciar.bat
```

Abre `http://localhost:8001` (interfaz) o `http://localhost:8001/docs` (Swagger).

En macOS/Linux utiliza `./instalar.sh` y `./iniciar.sh` tras conceder permiso de ejecución.

## 3. Prueba rápida

Nota **inventada** para demostración:

> Paciente con asma y lumbalgia. Niega fiebre. Se descarta infección urinaria.

Con el modo **híbrido**, el prototipo debería marcar J45.9 y M54.5 como confirmados; R50.9 como negado y N39.0 como descartado. Es una expectativa de prueba, no una indicación médica.

También puedes usar la API:

```json
{
  "nota": "Paciente con asma diagnosticada.",
  "proveedor": "ollama",
  "motor": "hibrido"
}
```

Endpoint: `POST /api/codificamed/analizar`. El campo `proveedor` admite `ollama`, `gemini` y `claude`. El campo `motor` admite `solo_reglas`, `solo_llm` y `hibrido`.

## 4. Componentes del proyecto

- `app/main.py`: API FastAPI y página principal.
- `app/codificamed.py`: detección de entidades, estado, selección del motor y filtrado de evidencias.
- `app/catalogo_cie10.py`: 22 códigos didácticos con sus patrones de búsqueda.
- `app/llm/`: clientes Ollama, Gemini y Claude.
- `app/static/codificamed.html`: interfaz web.
- `tests/`: 20 casos iniciales, 40 casos sintéticos de validación y evaluadores.
- `resultados/`: JSON de evaluaciones realizadas (sin notas reales de pacientes).
- `documentacion/`: informe y guion del video.

**Procesamiento real implementado:** entrada y validación de nota → comparación textual con expresiones regulares / catálogo → detección de negación y estado por contexto → solicitud JSON al LLM (si corresponde) → validación literal de evidencia → combinación y presentación. **No se implementó RAG con embeddings sobre CIE-10 en el módulo clínico**, aunque el proyecto de referencia AplicaTI sí lo utilizaba. No afirmar RAG como función activa en la exposición.

## 5. Reproducir la evaluación (40 casos ficticios)

Con servidor levantado y modelos configurados:

```powershell
.\.venv\Scripts\python.exe tests\evaluar_validacion.py --modo reglas
.\.venv\Scripts\python.exe tests\evaluar_validacion.py --modo api --proveedor ollama --motor solo_llm --timeout 180 --salida resultados/validacion_qwen_solo_llm_40.json
.\.venv\Scripts\python.exe tests\evaluar_validacion.py --modo api --proveedor ollama --motor hibrido --timeout 180 --salida resultados/validacion_ollama_hibrido_22.json
.\.venv\Scripts\python.exe tests\evaluar_validacion.py --modo api --proveedor gemini --motor solo_llm --timeout 180 --salida resultados/validacion_gemini_solo_llm_40.json
```

La evaluación mide pares `(código, estado)` mediante **micro-precisión, micro-recall y micro-F1**. Los resultados son reproducibles solo en condiciones aproximadas: los LLM externos y locales pueden variar con sus versiones, disponibilidad y parámetros. No comparar los resultados de `solo_llm` con un motor híbrido como si fueran las mismas arquitecturas.

| Configuración (40 casos) | Precisión | Recall | F1 | Tiempo medio |
|---|---:|---:|---:|---:|
| Reglas | 97,56% | 97,56% | 97,56% | 0,12 s |
| Qwen 2.5 3B, solo LLM | 81,82% | 21,95% | 34,62% | 15,83 s |
| Qwen + reglas, híbrido | 97,56% | 97,56% | 97,56% | 16,89 s |
| Gemini 3.5 Flash-Lite, solo LLM | 98,57% | 84,15% | 90,79% | 3,96 s |

Datos provienen de los JSON entregados. El filtro que exige evidencia literal permanece activo en el modo `solo_llm`, así que no se mide el LLM sin postprocesamiento. Las etiquetas son sintéticas, no verificadas por médicos. Este catálogo reducido y sus asignaciones no garantizan cumplimiento de las reglas de codificación clínica. Los resultados no avalan uso real.

## 6. Seguridad y entrega

- **Nunca** subir `.env` ni claves API, datos clínicos reales, `.venv`, bases de datos privadas ni caches.
- `.env.example` deja las credenciales vacías; `.gitignore` excluye `.env`.
- El ZIP de entrega fue preparado **sin** el `.env` del autor ni su entorno Python.
- El código y el informe deben acompañarse de un video de escritorio de **máximo 10 minutos mostrando el rostro en una esquina**, según la consigna.
- Referencias: [OMS, CIE-10 2019](https://icd.who.int/browse10/2019/en/), [Studer et al., CRISP-ML(Q), 2021](https://doi.org/10.3390/make3020020).

- ## Video demostrativo

El video presenta la metodología CRISP-ML(Q),
el funcionamiento con Ollama y Gemini,
y los resultados de evaluación del sistema.

[Ver o descargar el video demostrativo](https://github.com/DavidMv3/CodificaMed-PLN-CIE10/releases/tag/1.0)
