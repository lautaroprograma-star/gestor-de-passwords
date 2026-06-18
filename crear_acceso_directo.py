import os
import sys
import subprocess

def obtener_ruta_escritorio():
    """Obtiene la ruta del escritorio de forma segura (reutilizable)"""
    escritorio = os.path.join(os.path.expanduser("~"), "Desktop")
    
    if not os.path.exists(escritorio):
        escritorio = os.path.join(os.path.expanduser("~"), "Escritorio")
    
    if not os.path.exists(escritorio):
        try:
            os.makedirs(escritorio, exist_ok=True)
        except Exception:
            escritorio = os.path.expanduser("~")
    
    return escritorio


def crear_shortcut_windows(shortcut_path, target_path, work_dir, icon_location=None, description=None):
    """Crea un acceso directo .lnk en Windows usando un script VBS temporal"""
    vbs_path = os.path.join(work_dir, "crear_shortcut.vbs")
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write('Set shell = CreateObject("WScript.Shell")\n')
        f.write('Set sc = shell.CreateShortcut(WScript.Arguments(0))\n')
        f.write('sc.TargetPath = WScript.Arguments(1)\n')
        f.write('sc.WorkingDirectory = WScript.Arguments(2)\n')
        f.write('sc.WindowStyle = 1\n')
        if description is not None:
            f.write('sc.Description = WScript.Arguments(3)\n')
            if icon_location is not None:
                f.write('sc.IconLocation = WScript.Arguments(4)\n')
        elif icon_location is not None:
            f.write('sc.IconLocation = WScript.Arguments(3)\n')
        f.write('sc.Save\n')

    args = ["cscript", "//nologo", vbs_path, shortcut_path, target_path, work_dir]
    if description is not None:
        args.append(description)
    if icon_location is not None:
        args.append(icon_location)

    subprocess.run(args, check=True)
    os.remove(vbs_path)


def crear_acceso_directo():
    """Crea un acceso directo en el escritorio y un archivo portátil en la carpeta del programa"""
    escritorio = obtener_ruta_escritorio()
    
    # Ruta del programa principal
    directorio_actual = os.path.dirname(os.path.abspath(sys.argv[0]))
    programa_principal = os.path.join(directorio_actual, "gestor_contrasenas.py")
    
    if not os.path.exists(programa_principal):
        print(f"Error: No se encuentra {programa_principal}")
        print("Asegúrate de que 'gestor_contrasenas.py' esté en la misma carpeta")
        return False
    
    def escribir_bat(path, titulo):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'@echo off\n')
            f.write(f'title {titulo}\n')
            f.write(f'cd /d "{directorio_actual}"\n')
            f.write(f'"{python_exe}" "{programa_principal}"\n')
            f.write(f'if errorlevel 1 (\n')
            f.write(f'    echo.\n')
            f.write(f'    echo Error al ejecutar el programa.\n')
            f.write(f'    echo Asegurate de tener Python instalado.\n')
            f.write(f'    pause\n')
            f.write(f')\n')
    
    # Para Windows - Crear archivo .bat y un acceso directo con icono
    if sys.platform == "win32":
        bat_path = os.path.join(escritorio, "Gestor_Contrasenas.bat")
        portable_bat_name = "Gestor_Contrasenas_Portatil.bat"
        portable_bat_path = os.path.join(directorio_actual, portable_bat_name)
        portable_shortcut_path = os.path.join(escritorio, "Gestor_Contrasenas_Portatil.lnk")
        python_exe = sys.executable.replace('"', '')
        icon_location = f"{python_exe},0"
        try:
            escribir_bat(bat_path, "Gestor de Contraseñas PRO")
            escribir_bat(portable_bat_path, "Gestor de Contraseñas PRO - Portátil")
            crear_shortcut_windows(portable_shortcut_path, portable_bat_path, directorio_actual,
                                   icon_location=icon_location,
                                   description="Acceso directo portátil al Gestor de Contraseñas")
            print(f"✅ Acceso directo creado en: {bat_path}")
            print(f"✅ Archivo portátil creado en: {portable_bat_path}")
            print(f"✅ Atajo con icono creado en: {portable_shortcut_path}")
            print("📌 Usa el .bat portátil o el acceso directo con icono según prefieras")
            return True
        except Exception as e:
            print(f"Error al crear archivos .bat o atajos: {e}")
            return False
        
    # Para Linux/Mac
    else:
        sh_path = os.path.join(escritorio, "gestor_contrasenas.sh")
        try:
            with open(sh_path, "w") as f:
                f.write(f'#!/bin/bash\n')
                f.write(f'cd "{directorio_actual}"\n')
                f.write(f'python3 gestor_contrasenas.py\n')
            
            os.chmod(sh_path, 0o755)
            print(f"✅ Acceso directo creado en: {sh_path}")
            print("📌 Ejecuta: chmod +x gestor_contrasenas.sh && ./gestor_contrasenas.sh")
            return True
        except Exception as e:
            print(f"Error al crear .sh: {e}")
            return False

def crear_instalador_windows():
    """Crea un instalador simple para Windows"""
    if sys.platform != "win32":
        return False
    
    escritorio = obtener_ruta_escritorio()
    directorio_actual = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    install_path = os.path.join(escritorio, "Instalar_Gestor_Contrasenas.bat")
    python_exe = sys.executable.replace('"', '')
    try:
        with open(install_path, "w", encoding="utf-8") as f:
            f.write(f'@echo off\n')
            f.write(f'echo ========================================\n')
            f.write(f'echo   GESTOR DE CONTRASEÑAS PRO - INSTALADOR\n')
            f.write(f'echo ========================================\n')
            f.write(f'echo.\n')
            f.write(f'echo Instalando dependencias...\n')
            f.write(f'"{python_exe}" -m pip install cryptography openpyxl\n')
            f.write(f'echo.\n')
            f.write(f'echo Creando acceso directo...\n')
            f.write(f'cd /d "{directorio_actual}"\n')
            f.write(f'"{python_exe}" crear_acceso_directo.py\n')
            f.write(f'echo.\n')
            f.write(f'echo ¡Instalación completada!\n')
            f.write(f'echo.\n')
            f.write(f'pause\n')
        
        print(f"✅ Instalador creado en: {install_path}")
        print("📌 Ejecuta 'Instalar_Gestor_Contrasenas.bat' para instalar dependencias y crear acceso directo")
        return True
    except Exception as e:
        print(f"Error al crear instalador: {e}")
        return False

if __name__ == "__main__":
    print("========================================")
    print("  CREADOR DE ACCESO DIRECTO")
    print("========================================\n")
    
    crear_acceso_directo()
    
    if sys.platform == "win32":
        print("\n")
        crear_instalador_windows()
    
    print("\n✅ Proceso completado!")
    input("\nPresiona Enter para salir...")