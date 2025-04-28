import tkinter as tk
from tkinter import ttk  # Importar themed widgets
from tkinter import font
from tkinter.ttk import Style # Para configurar estilos
import time
from datetime import datetime
import os
import logging

# --- Configuración de Logging (sin cambios) ---
# logging.basicConfig(level=logging.INFO)

# --- Comprobación de Picamera2 (sin cambios) ---
try:
    from picamera2 import Picamera2, Preview
    picamera2_available = True
except ImportError:
    print("Error: La biblioteca picamera2 no se encontró.")
    print("Por favor, instálala con: sudo apt install python3-picamera2")
    picamera2_available = False
except Exception as e:
    print(f"Error al inicializar la cámara: {e}")
    print("Asegúrate de que la cámara esté conectada y habilitada en raspi-config.")
    picamera2_available = False

# --- Funciones de Cámara y Limpieza (sin cambios lógicos) ---

def tomar_foto():
    """Captura una foto usando Picamera2 y la guarda con timestamp."""
    if not picamera2_available:
        actualizar_estado("Error: picamera2 no disponible.", error=True)
        return

    actualizar_estado("Iniciando cámara...", info=True)
    root.update_idletasks()
    picam2 = None
    try:
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
        picam2.configure(config)
        picam2.start()

        actualizar_estado("Ajustando parámetros...", info=True)
        root.update_idletasks()
        time.sleep(2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"foto_{timestamp}.jpg"
        ruta_completa = os.path.join(os.getcwd(), nombre_archivo)

        actualizar_estado(f"Capturando foto: {nombre_archivo}...", info=True)
        root.update_idletasks()

        metadata = picam2.capture_file(ruta_completa)
        print("Metadatos de captura:", metadata)

        actualizar_estado(f"¡Foto guardada! -> {nombre_archivo}", success=True)

    except Exception as e:
        mensaje_error = f"Error al tomar foto: {e}"
        print(mensaje_error)
        actualizar_estado(mensaje_error, error=True)

    finally:
        if picam2 and picam2.started:
            picam2.stop()
            picam2.close()
            # Mantener el mensaje final pero indicar que la cámara se detuvo
            current_text = status_label.cget("text")
            current_fg = status_label.cget("foreground") # Necesitamos saber si era error o éxito
            actualizar_estado(current_text + "\nCámara detenida.",
                              error=(current_fg == COLOR_ERROR),
                              success=(current_fg == COLOR_SUCCESS),
                              info=(current_fg == COLOR_INFO))
            print("Cámara detenida y cerrada.")


def limpiar_estado():
    """Limpia el texto del campo de estado."""
    actualizar_estado("Listo.", info=True)

def actualizar_estado(mensaje, error=False, success=False, info=False):
    """Actualiza el texto y color del label de estado."""
    color = COLOR_DEFAULT
    if error:
        color = COLOR_ERROR
    elif success:
        color = COLOR_SUCCESS
    elif info:
        color = COLOR_INFO
    # Usamos configure para cambiar propiedades de ttk widgets
    status_label.configure(text=mensaje, foreground=color)

# --- Configuración de la Interfaz Gráfica Moderna (Tkinter + ttk) ---

root = tk.Tk()
root.title("Captura de Foto - Raspberry Pi")
root.geometry("500x250") # Un poco más grande para el padding

# --- Paleta de Colores y Fuentes ---
COLOR_PRIMARY = "#007bff"        # Azul primario
COLOR_SECONDARY = "#6c757d"       # Gris secundario
COLOR_SUCCESS = "#28a745"        # Verde éxito
COLOR_ERROR = "#dc3545"          # Rojo error
COLOR_INFO = "#17a2b8"           # Azul info/neutro
COLOR_BG = "#f8f9fa"             # Fondo claro
COLOR_FG = "#212529"             # Texto principal oscuro
COLOR_BTN_FG = "#ffffff"         # Texto en botones principales

root.configure(bg=COLOR_BG) # Configura el fondo de la ventana principal

# Fuentes
default_font_family = "Helvetica" # O prueba "Segoe UI", "Arial", etc.
button_font_style = font.Font(family=default_font_family, size=11, weight='bold')
status_font_style = font.Font(family=default_font_family, size=10)
COLOR_DEFAULT = COLOR_INFO # Color por defecto para el status

# --- Estilos ttk ---
style = Style(root)
# Elige un tema base (puede variar según el OS: 'clam', 'alt', 'default', 'classic')
# 'clam' suele ser una buena opción multiplataforma para personalizar
style.theme_use('clam')

# Configurar estilo base para botones TButton
style.configure('TButton',
                font=button_font_style,
                padding=(10, 5), # padding interno (horizontal, vertical)
                borderwidth=1,
                focusthickness=3,
                focuscolor='none') # Evita el anillo de foco feo a veces
style.map('TButton',
          foreground=[('disabled', '#adb5bd')], # Color texto deshabilitado
          background=[('disabled', '#e9ecef')]) # Color fondo deshabilitado

# Estilo para el botón primario (Tomar Foto)
style.configure('Primary.TButton',
                background=COLOR_PRIMARY,
                foreground=COLOR_BTN_FG)
style.map('Primary.TButton',
          background=[('active', '#0056b3'), # Color al presionar/hover
                     ('disabled', '#e9ecef')],
          foreground=[('disabled', '#adb5bd')])

# Estilo para el botón secundario (Limpiar)
style.configure('Secondary.TButton',
                background=COLOR_SECONDARY,
                foreground=COLOR_BTN_FG)
style.map('Secondary.TButton',
          background=[('active', '#5a6268'),
                     ('disabled', '#e9ecef')],
          foreground=[('disabled', '#adb5bd')])

# Estilo para el Label de estado
style.configure('Status.TLabel',
                font=status_font_style,
                padding=8,
                anchor=tk.W, # Alinear texto a la izquierda
                foreground=COLOR_DEFAULT, # Color inicial
                background=COLOR_BG) # Mismo fondo que la ventana


# --- Frame Principal para Contenido ---
# Usar un frame ayuda a organizar y aplicar padding general
content_frame = ttk.Frame(root, padding="20 20 20 20", style='TFrame') # Padding externo (izq, arriba, der, abajo)
content_frame.pack(fill=tk.BOTH, expand=True)

# Configurar el frame para que use el color de fondo
style.configure('TFrame', background=COLOR_BG)


# --- Widgets usando ttk ---

# 1. Botón para tomar foto (usando estilo 'Primary.TButton')
take_photo_button = ttk.Button(
    content_frame,
    text="Tomar Foto",
    command=tomar_foto,
    style='Primary.TButton', # Aplicar estilo personalizado
    state=tk.NORMAL if picamera2_available else tk.DISABLED # Estado inicial
)
# pack con padding externo (pady: arriba, abajo)
take_photo_button.pack(pady=(0, 15), fill=tk.X)

# 2. Campo (Label) para mostrar estado/mensajes (usando estilo 'Status.TLabel')
status_label = ttk.Label(
    content_frame,
    text="Haz clic en 'Tomar Foto'",
    style='Status.TLabel', # Aplicar estilo personalizado
    wraplength=440 # Ancho máximo antes de saltar línea (ajusta según tamaño ventana/padding)
)
# relief=tk.SOLID, borderwidth=1 # Opcional: si quieres un borde sutil
status_label.pack(pady=10, fill=tk.X)

# 3. Botón para limpiar el estado (usando estilo 'Secondary.TButton')
clear_button = ttk.Button(
    content_frame,
    text="Limpiar Mensaje",
    command=limpiar_estado,
    style='Secondary.TButton' # Aplicar estilo secundario
)
clear_button.pack(pady=(10, 0), fill=tk.X)


# --- Iniciar el bucle principal de Tkinter ---
if not picamera2_available:
     actualizar_estado("Error: picamera2 no disponible. Botón deshabilitado.", error=True)

root.mainloop()