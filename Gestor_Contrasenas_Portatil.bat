@echo off
title Gestor de Contraseñas PRO - Portátil
cd /d "c:\Users\juans\OneDrive\Desktop\algoritmo_programacion\GestorContrasenas"
"C:\Users\juans\AppData\Local\Python\pythoncore-3.14-64\python.exe" "c:\Users\juans\OneDrive\Desktop\algoritmo_programacion\GestorContrasenas\gestor_contrasenas.py"
if errorlevel 1 (
    echo.
    echo Error al ejecutar el programa.
    echo Asegurate de tener Python instalado.
    pause
)
