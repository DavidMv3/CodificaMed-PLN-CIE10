@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo === Instalacion de CodificaMed ===
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3.11 -m venv .venv
  ) else (
    python -m venv .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: No se pudo crear el entorno virtual. Instala Python 3.11 o superior.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: No se instalaron todas las dependencias.
  pause
  exit /b 1
)
if not exist ".env" copy ".env.example" ".env" >nul
echo Instalacion lista. Para el modelo local ejecuta: ollama pull qwen2.5:3b
echo Edita .env si vas a usar Gemini.
pause
