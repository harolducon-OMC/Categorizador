@echo off
setlocal
cd /d "%~dp0"
title Plataforma de Insights - instalacion

echo ===============================================
echo  Plataforma de Insights - Windows
echo  Preparando entorno e instalando dependencias
echo ===============================================

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual local...
    python -m venv .venv
    if errorlevel 1 goto error
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto error

python -m pip install -r requirements.txt
if errorlevel 1 goto error

python -c "import openai, streamlit; print('Dependencias listas. OpenAI SDK:', openai.__version__)"
if errorlevel 1 goto error

echo.
echo Abriendo la aplicacion...
python -m streamlit run Home.py
goto fin

:error
echo.
echo No se pudieron instalar las dependencias. Revisa tu conexion a internet y que Python este instalado.
echo Tambien puedes abrir PowerShell en esta carpeta y ejecutar:
echo   .\.venv\Scripts\Activate.ps1
echo   python -m pip install -r requirements.txt
pause
:fin
endlocal
