@echo off
chcp 65001 > nul
echo ========================================================
echo       SubvenRadar - Becas, Ayudas y Subvenciones
echo ========================================================
echo Iniciando servidor web para móvil y escritorio...

cd /d "%~dp0"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
