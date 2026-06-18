@echo off
title Instalador Gestor de Contraseñas PRO
color 0A

echo ========================================
echo   GESTOR DE CONTRASEÑAS PRO
echo   INSTALADOR AUTOMATICO
echo ========================================
echo.

echo [1/3] Verificando Python...
set "PY_CMD=python"
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python no esta instalado
        echo Por favor, instala Python desde https://python.org
        pause
        exit /b 1
    )
)
echo Python encontrado!
echo.

echo [2/3] Instalando dependencias...
"%PY_CMD%" -m pip install cryptography openpyxl
echo.

echo [3/3] Creando acceso directo...
"%PY_CMD%" crear_acceso_directo.py
echo.

echo ========================================
echo   INSTALACION COMPLETADA!
echo ========================================
echo.
echo Puedes ejecutar el programa desde:
echo - El acceso directo en tu escritorio
echo - O ejecutando: python gestor_contrasenas.py
echo.
echo Presiona cualquier tecla para salir...
pause >nul