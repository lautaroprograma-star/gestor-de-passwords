import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk
import csv
import os
import random
import string
import datetime
import json
import threading
import time
from cryptography.fernet import Fernet
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from functools import lru_cache

# =====================================================
# CONFIGURACION
# =====================================================

ARCHIVO_CSV = "contrasenas.csv"
ARCHIVO_KEY = "clave_secreta.key"
ARCHIVO_CONFIG = "configuracion.json"
CACHE_CONFIG = {}

# =====================================================
# UTILIDADES
# =====================================================

def leer_csv_seguro():
    """Lee el CSV y retorna filas, manejo de errores centralizado"""
    if not os.path.exists(ARCHIVO_CSV):
        return []
    
    try:
        with open(ARCHIVO_CSV, "r", encoding="utf-8") as archivo:
            lector = csv.reader(archivo)
            filas = list(lector)
            return filas[1:] if len(filas) > 1 else []  # Saltar encabezado
    except Exception as e:
        print(f"Error al leer CSV: {e}")
        return []

def obtener_ruta_escritorio():
    """Obtiene la ruta del escritorio de forma segura"""
    escritorio = os.path.join(os.path.expanduser("~"), "Desktop")
    
    if not os.path.exists(escritorio):
        escritorio = os.path.join(os.path.expanduser("~"), "Escritorio")
    
    if not os.path.exists(escritorio):
        try:
            os.makedirs(escritorio, exist_ok=True)
        except Exception:
            escritorio = os.path.expanduser("~")
    
    return escritorio

# =====================================================
# CIFRADO REAL (FERNET)
# =====================================================

def generar_o_cargar_clave():
    """Genera o carga una clave de cifrado"""
    if os.path.exists(ARCHIVO_KEY):
        with open(ARCHIVO_KEY, "rb") as archivo_clave:
            return archivo_clave.read()
    else:
        clave = Fernet.generate_key()
        with open(ARCHIVO_KEY, "wb") as archivo_clave:
            archivo_clave.write(clave)
        return clave

# Cargar clave de cifrado
CLAVE_CIFRADO = generar_o_cargar_clave()
cipher = Fernet(CLAVE_CIFRADO)

def encriptar(texto):
    """Cifra el texto usando Fernet"""
    return cipher.encrypt(texto.encode()).decode()

def desencriptar(texto):
    """Descifra el texto usando Fernet"""
    try:
        return cipher.decrypt(texto.encode()).decode()
    except Exception:
        return "[ERROR AL DESCIFRAR]"

# =====================================================
# CONFIGURACIÓN DE RECORDATORIOS
# =====================================================

def cargar_configuracion():
    """Carga la configuración de recordatorios (con caché)"""
    global CACHE_CONFIG
    if CACHE_CONFIG:
        return CACHE_CONFIG
    
    if os.path.exists(ARCHIVO_CONFIG):
        try:
            with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
                CACHE_CONFIG = json.load(f)
                return CACHE_CONFIG
        except Exception as e:
            print(f"Error cargando config: {e}")
    
    CACHE_CONFIG = {"recordatorio_activo": False, "dias_recordatorio": 90, "ultima_verificacion": None}
    return CACHE_CONFIG

def guardar_configuracion(config):
    """Guarda la configuración de recordatorios"""
    global CACHE_CONFIG
    CACHE_CONFIG = config.copy()
    try:
        with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")

def verificar_contraseñas_vencidas(dias):
    """Verifica si hay contraseñas que no se han actualizado en X días"""
    vencidas = []
    ahora = datetime.datetime.now()
    
    for fila in leer_csv_seguro():
        if len(fila) >= 3:
            try:
                fecha = datetime.datetime.strptime(fila[2], "%Y-%m-%d %H:%M:%S")
                if (ahora - fecha).days >= dias:
                    vencidas.append((fila[1], fila[2], fila[3] if len(fila) > 3 else "N/A"))
            except Exception:
                continue
    
    return vencidas

# Variable global para la ventana (se define después)
ventana = None

def iniciar_monitor_recordatorios():
    """Inicia un hilo para monitorear recordatorios"""
    def monitor():
        global ventana
        while True:
            try:
                config = cargar_configuracion()
                if config.get("recordatorio_activo", False):
                    dias = config.get("dias_recordatorio", 90)
                    vencidas = verificar_contraseñas_vencidas(dias)
                    
                    if vencidas and len(vencidas) > 0:
                        # Mostrar notificación (en el hilo principal)
                        if ventana:
                            ventana.after(0, lambda: mostrar_notificacion_recordatorio(vencidas, dias))
                        
                        # Actualizar última verificación
                        config["ultima_verificacion"] = datetime.datetime.now().isoformat()
                        guardar_configuracion(config)
                
                # Esperar 24 horas para la próxima verificación
                time.sleep(86400)  # 24 horas
            except Exception as e:
                print(f"Error en monitor: {e}")
                time.sleep(3600)  # Esperar 1 hora si hay error
    
    hilo = threading.Thread(target=monitor, daemon=True)
    hilo.start()

def mostrar_notificacion_recordatorio(vencidas, dias):
    """Muestra una notificación de contraseñas vencidas"""
    if not vencidas:
        return
    
    mensaje = f"⚠️ RECORDATORIO DE SEGURIDAD ⚠️\n\n"
    mensaje += f"Tiene {len(vencidas)} contraseña(s) que no se han actualizado en los últimos {dias} días:\n\n"
    
    for uso, fecha, seguridad in vencidas[:5]:  # Mostrar máximo 5
        mensaje += f"• {uso}: Última actualización {fecha}\n"
    
    if len(vencidas) > 5:
        mensaje += f"\n... y {len(vencidas) - 5} más."
    
    mensaje += f"\n\n¿Desea ver la lista completa?"
    
    if messagebox.askyesno("Recordatorio de Seguridad", mensaje):
        # Mostrar ventana de contraseñas vencidas
        mostrar_vencidas_detalle(vencidas)

def mostrar_vencidas_detalle(vencidas):
    """Muestra una ventana con el detalle de contraseñas vencidas"""
    global ventana
    ventana_vencidas = tk.Toplevel(ventana)
    ventana_vencidas.title("Contraseñas que requieren actualización")
    ventana_vencidas.geometry("600x400")
    ventana_vencidas.config(bg="#2b2b2b")
    
    # Centrar ventana
    ventana_vencidas.transient(ventana)
    ventana_vencidas.grab_set()
    
    tk.Label(ventana_vencidas, text="🔐 CONTRASEÑAS POR ACTUALIZAR",
            font=("Arial", 14, "bold"), bg="#2b2b2b", fg="#FF9800").pack(pady=10)
    
    # Crear treeview para mostrar las vencidas
    frame_tree = tk.Frame(ventana_vencidas, bg="#2b2b2b")
    frame_tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    tree = ttk.Treeview(frame_tree, columns=("Uso", "Fecha", "Seguridad"), show="headings", height=15)
    tree.heading("Uso", text="Uso")
    tree.heading("Fecha", text="Última actualización")
    tree.heading("Seguridad", text="Seguridad")
    
    tree.column("Uso", width=200)
    tree.column("Fecha", width=200)
    tree.column("Seguridad", width=150)
    
    for uso, fecha, seguridad in vencidas:
        tree.insert("", tk.END, values=(uso, fecha, seguridad))
    
    tree.pack(fill="both", expand=True)
    
    # Scrollbar
    scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)
    
    tk.Button(ventana_vencidas, text="Cerrar", command=ventana_vencidas.destroy,
             bg="#4CAF50", fg="white", font=("Arial", 10), width=15).pack(pady=10)

def configurar_recordatorio():
    """Configura el sistema de recordatorios"""
    global ventana
    config = cargar_configuracion()
    
    ventana_config = tk.Toplevel(ventana)
    ventana_config.title("Configurar Recordatorios")
    ventana_config.geometry("500x350")
    ventana_config.config(bg="#2b2b2b")
    ventana_config.transient(ventana)
    ventana_config.grab_set()
    
    # Centrar ventana
    ventana_config.update_idletasks()
    x = (ventana_config.winfo_screenwidth() // 2) - (500 // 2)
    y = (ventana_config.winfo_screenheight() // 2) - (350 // 2)
    ventana_config.geometry(f"500x350+{x}+{y}")
    
    tk.Label(ventana_config, text="⚙️ CONFIGURACIÓN DE RECORDATORIOS",
            font=("Arial", 14, "bold"), bg="#2b2b2b", fg="#4CAF50").pack(pady=15)
    
    # Frame para opciones
    frame_opciones = tk.Frame(ventana_config, bg="#2b2b2b")
    frame_opciones.pack(pady=20, padx=20, fill="both")
    
    # Checkbox para activar/desactivar
    activar_var = tk.BooleanVar(value=config.get("recordatorio_activo", False))
    tk.Checkbutton(frame_opciones, text="Activar recordatorios automáticos",
                  variable=activar_var, bg="#2b2b2b", fg="white", selectcolor="#2b2b2b",
                  font=("Arial", 11)).pack(anchor="w", pady=5)
    
    # Frame para días
    frame_dias = tk.Frame(frame_opciones, bg="#2b2b2b")
    frame_dias.pack(anchor="w", pady=10)
    
    tk.Label(frame_dias, text="Recordar después de:", bg="#2b2b2b", fg="white",
            font=("Arial", 10)).pack(side="left", padx=5)
    
    dias_var = tk.IntVar(value=config.get("dias_recordatorio", 90))
    spin_dias = tk.Spinbox(frame_dias, from_=30, to=365, textvariable=dias_var,
                          width=10, font=("Arial", 10))
    spin_dias.pack(side="left", padx=5)
    
    tk.Label(frame_dias, text="días sin actualizar", bg="#2b2b2b", fg="white",
            font=("Arial", 10)).pack(side="left", padx=5)
    
    # Información adicional
    frame_info = tk.Frame(ventana_config, bg="#1e1e1e", relief="groove", borderwidth=1)
    frame_info.pack(pady=15, padx=20, fill="both")
    
    tk.Label(frame_info, text="ℹ️ Información", bg="#1e1e1e", fg="#FF9800",
            font=("Arial", 10, "bold")).pack(anchor="w", pady=5, padx=10)
    
    tk.Label(frame_info, text="• Las contraseñas se consideran 'antiguas' si no se han actualizado\n  en el período seleccionado.\n• Recibirá una notificación automática cada 24 horas si hay\n  contraseñas que requieren actualización.\n• Es recomendable cambiar contraseñas cada 90 días.",
            bg="#1e1e1e", fg="white", font=("Arial", 9), justify="left").pack(pady=5, padx=10)
    
    # Botones
    frame_botones = tk.Frame(ventana_config, bg="#2b2b2b")
    frame_botones.pack(pady=15)
    
    def guardar_config():
        nueva_config = {
            "recordatorio_activo": activar_var.get(),
            "dias_recordatorio": dias_var.get(),
            "ultima_verificacion": config.get("ultima_verificacion")
        }
        guardar_configuracion(nueva_config)
        
        if activar_var.get():
            messagebox.showinfo("Configuración", f"Recordatorios activados.\nSe le notificará después de {dias_var.get()} días sin actualizar.")
        else:
            messagebox.showinfo("Configuración", "Recordatorios desactivados.")
        
        ventana_config.destroy()
    
    tk.Button(frame_botones, text="Guardar", command=guardar_config,
             bg="#4CAF50", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)
    
    tk.Button(frame_botones, text="Cancelar", command=ventana_config.destroy,
             bg="#d9534f", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)
    
    # Verificar ahora mismo
    def verificar_ahora():
        dias = dias_var.get()
        vencidas = verificar_contraseñas_vencidas(dias)
        if vencidas:
            mostrar_vencidas_detalle(vencidas)
        else:
            messagebox.showinfo("Verificación", f"No hay contraseñas que lleven más de {dias} días sin actualizar.")
    
    tk.Button(frame_botones, text="Verificar ahora", command=verificar_ahora,
             bg="#2196F3", fg="white", font=("Arial", 10), width=12).pack(side="left", padx=5)

# =====================================================
# ARCHIVO
# =====================================================

def inicializar_archivo():
    """Inicializa el archivo CSV si no existe"""
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, "w", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["contraseña", "uso", "fecha", "seguridad"])

def crear_backup():
    """Crea un backup del archivo CSV"""
    if os.path.exists(ARCHIVO_CSV):
        fecha_backup = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_backup = f"backup_contrasenas_{fecha_backup}.csv"
        with open(ARCHIVO_CSV, "r", encoding="utf-8") as origen:
            with open(archivo_backup, "w", encoding="utf-8") as destino:
                destino.write(origen.read())
        return archivo_backup
    return None

# =====================================================
# CLASE CONTRASEÑA
# =====================================================

class Contrasena:
    def __init__(self, longitud, mayusculas, minusculas, numeros, simbolos):
        self.longitud = longitud
        self.mayusculas = mayusculas
        self.minusculas = minusculas
        self.numeros = numeros
        self.simbolos = simbolos
        self.contrasena = self.generar()

    def generar(self):
        """Genera una contraseña aleatoria"""
        caracteres = ""
        
        if self.mayusculas:
            caracteres += string.ascii_uppercase
        if self.minusculas:
            caracteres += string.ascii_lowercase
        if self.numeros:
            caracteres += string.digits
        if self.simbolos:
            caracteres += "!@#$%^&*()_-+=<>?¿¡"
        
        if caracteres == "":
            caracteres = string.ascii_letters + string.digits
        
        # Asegurar al menos un carácter de cada tipo seleccionado
        contrasena_lista = []
        
        if self.mayusculas:
            contrasena_lista.append(random.choice(string.ascii_uppercase))
        if self.minusculas:
            contrasena_lista.append(random.choice(string.ascii_lowercase))
        if self.numeros:
            contrasena_lista.append(random.choice(string.digits))
        if self.simbolos:
            contrasena_lista.append(random.choice("!@#$%^&*()_-+=<>?¿¡"))
        
        # Completar el resto
        for _ in range(self.longitud - len(contrasena_lista)):
            contrasena_lista.append(random.choice(caracteres))
        
        # Mezclar
        random.shuffle(contrasena_lista)
        
        return ''.join(contrasena_lista)

    def nivel_seguridad(self):
        """Calcula el nivel de seguridad de la contraseña"""
        puntos = 0
        contrasena = self.contrasena
        
        if len(contrasena) >= 12:
            puntos += 2
        elif len(contrasena) >= 8:
            puntos += 1
        
        if any(c.isupper() for c in contrasena):
            puntos += 1
        if any(c.islower() for c in contrasena):
            puntos += 1
        if any(c.isdigit() for c in contrasena):
            puntos += 1
        if any(c in "!@#$%^&*()_-+=<>?¿¡" for c in contrasena):
            puntos += 2
        
        # Verificar variedad de caracteres
        tipos = sum([
            any(c.isupper() for c in contrasena),
            any(c.islower() for c in contrasena),
            any(c.isdigit() for c in contrasena),
            any(c in "!@#$%^&*()_-+=<>?¿¡" for c in contrasena)
        ])
        
        if tipos >= 3:
            puntos += 1
        if tipos == 4:
            puntos += 1
        
        if puntos <= 3:
            return "DÉBIL"
        elif puntos <= 6:
            return "MEDIA"
        else:
            return "FUERTE"

    def guardar(self, uso):
        """Guarda la contraseña en el archivo CSV"""
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seguridad = self.nivel_seguridad()
        contraseña_encriptada = encriptar(self.contrasena)
        
        with open(ARCHIVO_CSV, "a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow([contraseña_encriptada, uso, fecha, seguridad])

# =====================================================
# FUNCIONES DE LA INTERFAZ
# =====================================================

def copiar_al_portapapeles():
    """Copia la contraseña generada al portapapeles"""
    contraseña = resultado.get()
    if contraseña:
        ventana.clipboard_clear()
        ventana.clipboard_append(contraseña)
        messagebox.showinfo("Copiado", "Contraseña copiada al portapapeles")
    else:
        messagebox.showwarning("Aviso", "No hay contraseña para copiar")

def crear_contrasena():
    """Crea una nueva contraseña"""
    try:
        longitud = int(entry_longitud.get())
        if longitud < 4:
            messagebox.showwarning("Aviso", "La longitud mínima es 4 caracteres")
            return
        if longitud > 128:
            messagebox.showwarning("Aviso", "La longitud máxima es 128 caracteres")
            return
    except ValueError:
        messagebox.showerror("Error", "Ingrese una longitud válida (número entero)")
        return
    
    uso = entry_uso.get().strip()
    if not uso:
        messagebox.showwarning("Aviso", "Por favor, ingrese un uso para esta contraseña")
        return
    
    # Verificar si al menos una opción está seleccionada
    if not any([var_mayus.get(), var_minus.get(), var_numeros.get(), var_simbolos.get()]):
        messagebox.showwarning("Aviso", "Seleccione al menos un tipo de carácter")
        return
    
    nueva = Contrasena(
        longitud,
        var_mayus.get(),
        var_minus.get(),
        var_numeros.get(),
        var_simbolos.get()
    )
    
    resultado.set(nueva.contrasena)
    seguridad_valor = nueva.nivel_seguridad()
    seguridad.set(seguridad_valor)
    
    # Cambiar color según seguridad
    if seguridad_valor == "FUERTE":
        entry_seguridad.config(fg="green")
    elif seguridad_valor == "MEDIA":
        entry_seguridad.config(fg="orange")
    else:
        entry_seguridad.config(fg="red")
    
    nueva.guardar(uso)
    actualizar_tabla()
    
    # Limpiar campo de uso después de guardar
    entry_uso.delete(0, tk.END)
    
    messagebox.showinfo("Éxito", f"Contraseña creada correctamente.\nNivel de seguridad: {seguridad_valor}")

def actualizar_tabla(filtro=""):
    """Actualiza la tabla con las contraseñas (opcionalmente filtradas)"""
    for fila in tabla.get_children():
        tabla.delete(fila)
    
    filtro_lower = filtro.lower() if filtro else ""
    
    for fila in leer_csv_seguro():
        if len(fila) >= 4:
            try:
                contraseña_real = desencriptar(fila[0])
                uso = fila[1]
                
                # Aplicar filtro
                if filtro_lower and filtro_lower not in uso.lower() and filtro_lower not in contraseña_real.lower():
                    continue
                
                # Color según seguridad
                seguridad = fila[3]
                tags = ("fuerte",) if seguridad == "FUERTE" else ("media",) if seguridad == "MEDIA" else ("debil",)
                
                tabla.insert("", tk.END, values=(contraseña_real, uso, fila[2], seguridad), tags=tags)
            except Exception as e:
                print(f"Error al procesar fila: {e}")
                continue

def buscar_contrasena():
    """Busca contraseñas por uso o nombre"""
    filtro = simpledialog.askstring("Buscar", "Ingrese texto a buscar:")
    if filtro is not None:
        actualizar_tabla(filtro)

def eliminar_contrasena():
    """Elimina la contraseña seleccionada"""
    seleccion = tabla.selection()
    if not seleccion:
        messagebox.showwarning("Aviso", "Seleccione una contraseña para eliminar")
        return
    
    if not messagebox.askyesno("Confirmar", "¿Está seguro de eliminar esta contraseña?"):
        return
    
    item = tabla.item(seleccion)
    valores = item["values"]
    contraseña_a_eliminar = str(valores[0])
    
    # Crear backup
    crear_backup()
    
    filas = []
    with open(ARCHIVO_CSV, "r", encoding="utf-8") as archivo:
        filas = list(csv.reader(archivo))
    
    # Mantener encabezado y filtrar la contraseña
    nuevas_filas = [filas[0]]
    for fila in filas[1:]:
        if len(fila) >= 4:
            try:
                if desencriptar(fila[0]) != contraseña_a_eliminar:
                    nuevas_filas.append(fila)
            except:
                nuevas_filas.append(fila)
    
    try:
        with open(ARCHIVO_CSV, "w", newline="", encoding="utf-8") as archivo:
            csv.writer(archivo).writerows(nuevas_filas)
        actualizar_tabla()
        messagebox.showinfo("Éxito", "Contraseña eliminada correctamente")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo eliminar: {e}")

def exportar_excel():
    """Exporta las contraseñas a un archivo Excel"""
    try:
        crear_backup()
        nombre_archivo = f"contrasenas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Contraseñas"
        
        # Encabezados con estilo
        encabezados = ["Contraseña", "Uso", "Fecha", "Seguridad"]
        ws.append(encabezados)
        
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        
        for celda in ws[1]:
            celda.font = header_font
            celda.fill = header_fill
            celda.alignment = Alignment(horizontal="center")
        
        # Agregar datos desde CSV
        for fila in leer_csv_seguro():
            if len(fila) >= 4:
                try:
                    ws.append([desencriptar(fila[0]), fila[1], fila[2], fila[3]])
                except Exception as e:
                    print(f"Error desencriptando: {e}")
        
        # Ajustar ancho de columnas
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 50)
        
        wb.save(nombre_archivo)
        messagebox.showinfo("Éxito", f"Excel exportado correctamente:\n{nombre_archivo}")
        
        if messagebox.askyesno("Abrir archivo", "¿Desea abrir el archivo exportado?"):
            os.startfile(nombre_archivo)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar el Excel:\n{e}")

def mostrar_estadisticas():
    """Muestra estadísticas de las contraseñas"""
    total = fuerte = media = debil = 0
    
    for fila in leer_csv_seguro():
        if len(fila) >= 4:
            total += 1
            seguridad = fila[3]
            if seguridad == "FUERTE":
                fuerte += 1
            elif seguridad == "MEDIA":
                media += 1
            else:
                debil += 1
    
    stats = f"""ESTADÍSTICAS DE CONTRASEÑAS

Total de contraseñas: {total}
Contraseñas FUERTES: {fuerte} ({fuerte*100//total if total > 0 else 0}%)
Contraseñas MEDIAS: {media} ({media*100//total if total > 0 else 0}%)
Contraseñas DÉBILES: {debil} ({debil*100//total if total > 0 else 0}%)

Recomendación:
- Use contraseñas de al menos 12 caracteres
- Combine mayúsculas, minúsculas, números y símbolos
- No reutilice contraseñas
- Cambie sus contraseñas periódicamente
"""
    
    messagebox.showinfo("Estadísticas", stats)

def verificar_ahora():
    """Verifica manualmente contraseñas vencidas"""
    config = cargar_configuracion()
    dias = config.get("dias_recordatorio", 90)
    vencidas = verificar_contraseñas_vencidas(dias)
    
    if vencidas:
        mostrar_vencidas_detalle(vencidas)
    else:
        messagebox.showinfo("Verificación", f"No hay contraseñas que lleven más de {dias} días sin actualizar.")

# =====================================================
# INTERFAZ PRINCIPAL RESPONSIVE
# =====================================================

# Inicializar archivo
inicializar_archivo()

# Crear ventana principal
ventana = tk.Tk()
ventana.title("Gestor de Contraseñas PRO")
ventana.geometry("1200x700")
ventana.minsize(800, 600)
ventana.config(bg="#1e1e1e")

# Hacer la ventana responsive
ventana.grid_rowconfigure(0, weight=1)
ventana.grid_columnconfigure(0, weight=1)

# Configurar estilos
style = ttk.Style()
style.theme_use("default")
style.configure("Treeview", 
               background="#2b2b2b",
               foreground="white",
               rowheight=28,
               fieldbackground="#2b2b2b",
               font=("Arial", 10))
style.configure("Treeview.Heading",
               background="#366092",
               foreground="white",
               font=("Arial", 11, "bold"))
style.map('Treeview', background=[('selected', '#4F81BD')])

# Frame principal con grid para responsive
main_frame = tk.Frame(ventana, bg="#1e1e1e")
main_frame.pack(fill="both", expand=True, padx=10, pady=10)
main_frame.grid_rowconfigure(1, weight=1)
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_columnconfigure(1, weight=2)

# Título
titulo = tk.Label(main_frame, text="🔐 GESTOR DE CONTRASEÑAS PRO 🔐",
                 font=("Arial", 24, "bold"),
                 bg="#1e1e1e", fg="white")
titulo.grid(row=0, column=0, columnspan=2, pady=10)

# Panel izquierdo (generación) - Responsive
frame_izquierdo = tk.Frame(main_frame, bg="#2b2b2b", padx=15, pady=15,
                          relief="groove", borderwidth=2)
frame_izquierdo.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
frame_izquierdo.grid_columnconfigure(1, weight=1)

# Título sección
tk.Label(frame_izquierdo, text="GENERAR CONTRASEÑA",
        font=("Arial", 14, "bold"),
        bg="#2b2b2b", fg="#4CAF50").grid(row=0, column=0, columnspan=2, pady=(0, 10))

# Longitud
tk.Label(frame_izquierdo, text="Longitud:", bg="#2b2b2b", fg="white",
        font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
entry_longitud = tk.Entry(frame_izquierdo, width=15, font=("Arial", 10))
entry_longitud.grid(row=1, column=1, pady=5, padx=10, sticky="ew")
entry_longitud.insert(0, "16")

# Uso
tk.Label(frame_izquierdo, text="Uso (ej: Gmail, FB):",
        bg="#2b2b2b", fg="white", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
entry_uso = tk.Entry(frame_izquierdo, width=25, font=("Arial", 10))
entry_uso.grid(row=2, column=1, pady=5, padx=10, sticky="ew")

# Checkboxes
var_mayus = tk.BooleanVar(value=True)
var_minus = tk.BooleanVar(value=True)
var_numeros = tk.BooleanVar(value=True)
var_simbolos = tk.BooleanVar(value=True)

frame_check = tk.Frame(frame_izquierdo, bg="#2b2b2b")
frame_check.grid(row=3, column=0, columnspan=2, pady=10)

tk.Checkbutton(frame_check, text="Mayúsculas", variable=var_mayus,
              bg="#2b2b2b", fg="white", selectcolor="#2b2b2b",
              font=("Arial", 9)).pack(side="left", padx=5)
tk.Checkbutton(frame_check, text="Minúsculas", variable=var_minus,
              bg="#2b2b2b", fg="white", selectcolor="#2b2b2b",
              font=("Arial", 9)).pack(side="left", padx=5)
tk.Checkbutton(frame_check, text="Números", variable=var_numeros,
              bg="#2b2b2b", fg="white", selectcolor="#2b2b2b",
              font=("Arial", 9)).pack(side="left", padx=5)
tk.Checkbutton(frame_check, text="Símbolos", variable=var_simbolos,
              bg="#2b2b2b", fg="white", selectcolor="#2b2b2b",
              font=("Arial", 9)).pack(side="left", padx=5)

# Botón generar
btn_generar = tk.Button(frame_izquierdo, text="✨ GENERAR ✨",
                       command=crear_contrasena,
                       bg="#4CAF50", fg="white", 
                       font=("Arial", 11, "bold"),
                       height=2)
btn_generar.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")

# Resultado
tk.Label(frame_izquierdo, text="Contraseña:", bg="#2b2b2b", 
        fg="white", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="w", pady=5)

frame_pass = tk.Frame(frame_izquierdo, bg="#2b2b2b")
frame_pass.grid(row=5, column=1, pady=5, padx=10, sticky="ew")
frame_pass.grid_columnconfigure(0, weight=1)

resultado = tk.StringVar()
entry_resultado = tk.Entry(frame_pass, textvariable=resultado, 
                          font=("Arial", 10, "bold"), 
                          state="readonly", readonlybackground="#3a3a3a")
entry_resultado.grid(row=0, column=0, sticky="ew")

btn_copiar = tk.Button(frame_pass, text="📋", command=copiar_al_portapapeles,
                      bg="#2196F3", fg="white", font=("Arial", 9), width=3)
btn_copiar.grid(row=0, column=1, padx=(5, 0))

# Seguridad
tk.Label(frame_izquierdo, text="Seguridad:", bg="#2b2b2b", 
        fg="white", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky="w", pady=5)
seguridad = tk.StringVar()
entry_seguridad = tk.Entry(frame_izquierdo, textvariable=seguridad, 
                          font=("Arial", 10, "bold"),
                          state="readonly", readonlybackground="#3a3a3a")
entry_seguridad.grid(row=6, column=1, pady=5, padx=10, sticky="ew")

# Botones adicionales
btn_recordatorio = tk.Button(frame_izquierdo, text="⏰ Configurar Recordatorio", 
                            command=configurar_recordatorio,
                            bg="#FF9800", fg="white", font=("Arial", 10))
btn_recordatorio.grid(row=7, column=0, columnspan=2, pady=5, sticky="ew")

btn_verificar = tk.Button(frame_izquierdo, text="🔍 Verificar ahora", 
                         command=verificar_ahora,
                         bg="#2196F3", fg="white", font=("Arial", 10))
btn_verificar.grid(row=8, column=0, columnspan=2, pady=5, sticky="ew")

# Panel derecho (tabla) - Responsive
frame_derecho = tk.Frame(main_frame, bg="#1e1e1e")
frame_derecho.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
frame_derecho.grid_rowconfigure(1, weight=1)
frame_derecho.grid_columnconfigure(0, weight=1)

# Frame de búsqueda
frame_busqueda = tk.Frame(frame_derecho, bg="#1e1e1e")
frame_busqueda.grid(row=0, column=0, sticky="ew", pady=(0, 5))
frame_busqueda.grid_columnconfigure(4, weight=1)

btn_buscar = tk.Button(frame_busqueda, text="🔍 Buscar", 
                      command=buscar_contrasena,
                      bg="#FF9800", fg="white", font=("Arial", 9))
btn_buscar.grid(row=0, column=0, padx=(0, 5))

btn_estadisticas = tk.Button(frame_busqueda, text="📊 Estadísticas", 
                            command=mostrar_estadisticas,
                            bg="#9C27B0", fg="white", font=("Arial", 9))
btn_estadisticas.grid(row=0, column=1, padx=5)

btn_excel = tk.Button(frame_busqueda, text="📊 Exportar Excel", 
                     command=exportar_excel,
                     bg="#28a745", fg="white", font=("Arial", 9))
btn_excel.grid(row=0, column=2, padx=5)

btn_eliminar = tk.Button(frame_busqueda, text="🗑️ Eliminar", 
                        command=eliminar_contrasena,
                        bg="#d9534f", fg="white", font=("Arial", 9))
btn_eliminar.grid(row=0, column=3, padx=(5, 0))

# Tabla
tabla = ttk.Treeview(frame_derecho, columns=("contraseña", "uso", "fecha", "seguridad"), 
                     show="headings", height=15)
tabla.tag_configure("fuerte", background="#1e3a1e")
tabla.tag_configure("media", background="#3a2a1e")
tabla.tag_configure("debil", background="#3a1e1e")

tabla.heading("contraseña", text="Contraseña")
tabla.heading("uso", text="Uso")
tabla.heading("fecha", text="Fecha")
tabla.heading("seguridad", text="Seguridad")

tabla.column("contraseña", width=250)
tabla.column("uso", width=180)
tabla.column("fecha", width=160)
tabla.column("seguridad", width=100)

# Scrollbar
scrollbar = ttk.Scrollbar(frame_derecho, orient="vertical", command=tabla.yview)
tabla.configure(yscrollcommand=scrollbar.set)

tabla.grid(row=1, column=0, sticky="nsew")
scrollbar.grid(row=1, column=1, sticky="ns")

# Cargar tabla
actualizar_tabla()

# Atajos de teclado
ventana.bind('<Delete>', lambda e: eliminar_contrasena())
ventana.bind('<Control-c>', lambda e: copiar_al_portapapeles())
ventana.bind('<Control-f>', lambda e: buscar_contrasena())
ventana.bind('<Control-g>', lambda e: crear_contrasena())

# Iniciar monitor de recordatorios
iniciar_monitor_recordatorios()

# Mensaje de bienvenida
messagebox.showinfo("Bienvenido", 
                   "¡Bienvenido al Gestor de Contraseñas PRO!\n\n"
                   "Características:\n"
                   "✓ Generación de contraseñas seguras\n"
                   "✓ Cifrado real (Fernet)\n"
                   "✓ Exportación a Excel\n"
                   "✓ Búsqueda y filtrado\n"
                   "✓ Estadísticas\n"
                   "✓ Recordatorios personalizables\n\n"
                   "Atajos de teclado:\n"
                   "Ctrl+G - Generar contraseña\n"
                   "Ctrl+F - Buscar\n"
                   "Ctrl+C - Copiar\n"
                   "Supr - Eliminar selección")

# Loop principal
ventana.mainloop()