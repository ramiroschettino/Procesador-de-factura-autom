@echo off
echo ========================================
echo  Iniciando Backend - Sistema Facturas IA
echo ========================================
echo.

REM Activar el entorno virtual
call venv\Scripts\activate.bat

REM Verificar que el entorno virtual está activado
if "%VIRTUAL_ENV%"=="" (
    echo ERROR: No se pudo activar el entorno virtual
    echo Por favor ejecuta setup.bat primero
    pause
    exit /b 1
)

echo Entorno virtual activado: %VIRTUAL_ENV%
echo.

REM Ejecutar el servidor API
echo Iniciando servidor en http://localhost:5000
echo.
echo IMPORTANTE: Deja esta ventana abierta mientras uses la aplicacion
echo Presiona Ctrl+C para detener el servidor
echo.

cd backend
python api.py

pause
