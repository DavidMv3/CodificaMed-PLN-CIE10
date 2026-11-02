@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Primero ejecuta instalar.bat
  pause
  exit /b 1
)
if not exist .env (
  echo Falta .env: copia .env.example a .env y configura tus modelos.
  pause
  exit /b 1
)
set PUERTO=8001
for /f "tokens=2 delims==" %%a in ('findstr /b "PUERTO=" .env') do set PUERTO=%%a
echo === CodificaMed ===
echo Aplicacion: http://localhost:%PUERTO%
echo Documentacion API: http://localhost:%PUERTO%/docs
echo Detener con Ctrl + C
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %PUERTO%
pause
