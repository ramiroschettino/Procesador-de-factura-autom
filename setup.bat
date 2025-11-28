@echo off
echo ========================================
echo  Configurando Sistema de Facturas IA
echo ========================================
echo.

REM Verificar si existe el venv
if exist venv (
    echo El entorno virtual ya existe.
    echo.
) else (
    echo Creando entorno virtual...
    python -m venv venv
    echo.
)

REM Activar el entorno virtual
call venv\Scripts\activate.bat

REM Instalar/actualizar dependencias
echo Instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================
echo  Configuracion completada
echo ========================================
echo.
echo Ahora puedes ejecutar:
echo   - run_backend.bat (para iniciar el servidor)
echo   - O abrir index.html en tu navegador
pause
