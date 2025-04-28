import tkinter as tk
from tkinter import ttk, font
from tkinter.ttk import Style
import time
from datetime import datetime
import os
import logging
from PIL import Image, ImageTk # Necesario para mostrar imágenes en Tkinter

# --- Configuración de Logging (sin cambios) ---
# logging.basicConfig(level=logging.INFO)

# --- Comprobación de Picamera2 (sin cambios) ---
try:
    from picamera2 import Picamera2
    picamera2_available = True
except ImportError:
    print("Error: La biblioteca picamera2 no se encontró.")
    print("Por favor, instálala con: sudo apt install python3-picamera2")
    picamera2_available = False
except Exception as e:
    print(f"Error al inicializar la cámara: {e}")
    print("Asegúrate de que la cámara esté conectada y habilitada en raspi-config.")
    picamera2_available = False

# --- Variables Globales ---
last_photo_path = None # Para guardar la ruta de la última foto tomada

# --- Funciones de Cámara y Limpieza ---

def tomar_foto():
    """Captura una foto, la muestra en el label y actualiza el texto."""
    global last_photo_path
    if not picamera2_available:
        actualizar_estado("Error: picamera2 no disponible.", error=True)
        return

    actualizar_estado("Iniciando cámara...", info=True)
    root.update_idletasks()
    picam2 = None
    try:
        picam2 = Picamera2()
        # Configuración para captura y para preview (que usaremos para la imagen en GUI)
        # Una resolución más baja para el display puede ser más eficiente
        config = picam2.create_still_configuration(
            main={"size": (1920, 1080)}, # Alta resolución para guardar
            lores={"size": (640, 480)},   # Baja resolución para eficiencia (opcional)
            display="lores"               # Stream a usar si hubiera preview en ventana separada
        )
        picam2.configure(config)
        picam2.start()

        actualizar_estado("Ajustando parámetros...", info=True)
        root.update_idletasks()
        time.sleep(2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"foto_{timestamp}.jpg"
        ruta_completa = os.path.join(os.getcwd(), nombre_archivo)
        last_photo_path = ruta_completa # Guarda la ruta

        actualizar_estado(f"Capturando foto: {nombre_archivo}...", info=True)
        root.update_idletasks()

        metadata = picam2.capture_file(ruta_completa)
        print("Metadatos de captura:", metadata)

        mostrar_imagen(ruta_completa) # Llama a la función para mostrar la imagen
        actualizar_estado(f"Foto guardada: {nombre_archivo}\n¡Mostrando previsualización!", success=True)

    except Exception as e:
        mensaje_error = f"Error al tomar foto: {e}"
        print(mensaje_error)
        actualizar_estado(mensaje_error, error=True)
        last_photo_path = None # Resetea si hubo error
        limpiar_imagen() # Limpia el display de imagen si falla

    finally:
        if picam2 and picam2.started:
            picam2.stop()
            picam2.close()
            print("Cámara detenida y cerrada.")
            # No sobrescribir el mensaje final de éxito/error
            current_text = text_area.get("1.0", tk.END).strip()
            if current_text: # Solo añade si ya hay texto
                 actualizar_estado(current_text + "\n(Cámara detenida)", append=True)


def mostrar_imagen(ruta_imagen):
    """Carga y muestra la imagen en el image_label."""
    try:
        # Abrir la imagen original
        img = Image.open(ruta_imagen)

        # Redimensionar la imagen para que quepa en el label
        # Obtener tamaño del label (puede ser necesario forzar actualización de layout)
        image_label.update_idletasks()
        label_width = image_label.winfo_width()
        label_height = image_label.winfo_height()

        # Prevenir división por cero si el label no tiene tamaño aún
        if label_width < 1 or label_height < 1:
             label_width = 400 # Tamaño por defecto razonable
             label_height = 300

        img.thumbnail((label_width - 10, label_height - 10), Image.Resampling.LANCZOS) # -10 para pequeño margen

        # Convertir a formato Tkinter
        photo = ImageTk.PhotoImage(img)

        # Mostrar en el label
        image_label.configure(image=photo, text="") # Quitar texto placeholder
        image_label.image = photo # ¡IMPORTANTE! Guardar referencia para evitar garbage collection

    except Exception as e:
        print(f"Error al mostrar imagen: {e}")
        actualizar_estado(f"Error al mostrar imagen: {e}", error=True, append=True)
        limpiar_imagen()

def limpiar_campos():
    """Limpia el texto del área de texto y la imagen."""
    global last_photo_path
    text_area.delete('1.0', tk.END) # Borra todo el texto
    text_area.insert('1.0', "Listo.") # Pone el estado inicial
    text_area.tag_remove(tk.ALL, "1.0", tk.END) # Quita cualquier tag de color
    text_area.tag_add("info", "1.0", tk.END) # Aplica tag de info
    limpiar_imagen()
    last_photo_path = None

def limpiar_imagen():
    """Quita la imagen del label y pone el texto placeholder."""
    image_label.configure(image=None, text="Imagen capturada aparecerá aquí")
    image_label.image = None # Limpiar referencia

def actualizar_estado(mensaje, error=False, success=False, info=False, append=False):
    """Actualiza el texto y color en el área de texto."""
    # Definir tags para colores si no existen
    if not "error" in text_area.tag_names():
        text_area.tag_configure("error", foreground=COLOR_ERROR)
    if not "success" in text_area.tag_names():
        text_area.tag_configure("success", foreground=COLOR_SUCCESS)
    if not "info" in text_area.tag_names():
        text_area.tag_configure("info", foreground=COLOR_INFO)

    # Determinar tag a usar
    tag = None
    if error: tag = "error"
    elif success: tag = "success"
    elif info: tag = "info"

    # Borrar contenido anterior si no es append
    if not append:
        text_area.delete("1.0", tk.END)

    # Insertar nuevo mensaje
    start_index = text_area.index(tk.END + "-1c") # Índice justo antes del final
    text_area.insert(tk.END, mensaje + "\n")
    end_index = text_area.index(tk.END + "-1c") # Índice final después de insertar

    # Aplicar tag si corresponde
    if tag:
        text_area.tag_add(tag, start_index, end_index)

    # Auto-scroll al final
    text_area.see(tk.END)


# --- Configuración de la Interfaz Gráfica (Tkinter + ttk + grid) ---

root = tk.Tk()
root.title("Capturadora Raspberry Pi")
root.geometry("800x450") # Tamaño inicial más ancho

# --- Paleta de Colores y Fuentes (igual que antes) ---
COLOR_PRIMARY = "#007bff"
COLOR_SECONDARY = "#6c757d"
COLOR_SUCCESS = "#28a745"
COLOR_ERROR = "#dc3545"
COLOR_INFO = "#17a2b8"
COLOR_BG = "#f8f9fa"
COLOR_FG = "#212529"
COLOR_BTN_FG = "#ffffff"
COLOR_PLACEHOLDER_BG = "#e9ecef" # Gris claro para placeholder de imagen

root.configure(bg=COLOR_BG)

default_font_family = "Helvetica"
button_font_style = font.Font(family=default_font_family, size=11, weight='bold')
status_font_style = font.Font(family=default_font_family, size=10)
text_area_font_style = font.Font(family=default_font_family, size=10)
placeholder_font_style = font.Font(family=default_font_family, size=12, slant='italic')

# --- Estilos ttk (igual que antes, añadiendo para placeholder) ---
style = Style(root)
style.theme_use('clam')

style.configure('TButton', font=button_font_style, padding=(10, 5), borderwidth=1)
style.map('TButton', foreground=[('disabled', '#adb5bd')], background=[('disabled', '#e9ecef')])

style.configure('Primary.TButton', background=COLOR_PRIMARY, foreground=COLOR_BTN_FG)
style.map('Primary.TButton', background=[('active', '#0056b3'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])

style.configure('Secondary.TButton', background=COLOR_SECONDARY, foreground=COLOR_BTN_FG)
style.map('Secondary.TButton', background=[('active', '#5a6268'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])

# Estilo para el Frame principal y el de la derecha
style.configure('TFrame', background=COLOR_BG)

# Estilo para el Label de la imagen (placeholder)
style.configure('ImagePlaceholder.TLabel',
                background=COLOR_PLACEHOLDER_BG,
                foreground=COLOR_SECONDARY, # Color del texto placeholder
                font=placeholder_font_style,
                anchor=tk.CENTER,
                relief=tk.SOLID, # Borde sólido
                borderwidth=1)

# --- Layout con Grid ---

# Frame principal para padding general
main_frame = ttk.Frame(root, padding="10 10 10 10", style='TFrame')
main_frame.pack(fill=tk.BOTH, expand=True)

# Configurar las columnas del main_frame para que se expandan
# Columna 0 (imagen) será más ancha que Columna 1 (controles)
main_frame.columnconfigure(0, weight=3)
main_frame.columnconfigure(1, weight=1)
# Configurar fila única para que se expanda verticalmente
main_frame.rowconfigure(0, weight=1)

# --- Columna Izquierda (Imagen) ---
image_label = ttk.Label(main_frame,
                        text="Imagen capturada aparecerá aquí",
                        style='ImagePlaceholder.TLabel')
image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0) # nsew = N, S, E, W (fill)

# --- Columna Derecha (Controles) ---
right_frame = ttk.Frame(main_frame, style='TFrame', padding=(5, 0)) # Padding izquierdo y sin padding vertical interno
right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

# Configurar grid dentro del right_frame
right_frame.rowconfigure(0, weight=3) # Área de texto ocupa más espacio
right_frame.rowconfigure(1, weight=0) # Botón Foto
right_frame.rowconfigure(2, weight=0) # Botón Limpiar
right_frame.columnconfigure(0, weight=1) # Única columna se expande

# 1. Campo de Texto (tk.Text)
text_area = tk.Text(right_frame,
                    height=10, # Altura inicial en líneas
                    width=30,  # Ancho inicial en caracteres
                    wrap=tk.WORD, # Salto de línea por palabra
                    font=text_area_font_style,
                    relief=tk.SOLID,
                    borderwidth=1,
                    fg=COLOR_FG, # Color de texto normal
                    bg=COLOR_PLACEHOLDER_BG) # Fondo similar al placeholder
text_area.grid(row=0, column=0, sticky="nsew", pady=(0, 10)) # Ocupa espacio, padding abajo

# Configurar tags de color para el Text widget
text_area.tag_configure("error", foreground=COLOR_ERROR)
text_area.tag_configure("success", foreground=COLOR_SUCCESS)
text_area.tag_configure("info", foreground=COLOR_INFO)

# 2. Botón Tomar Foto
take_photo_button = ttk.Button(
    right_frame,
    text="Foto", # Texto como en la imagen
    command=tomar_foto,
    style='Primary.TButton',
    state=tk.NORMAL if picamera2_available else tk.DISABLED
)
take_photo_button.grid(row=1, column=0, sticky="ew", pady=5) # Se expande horizontalmente

# 3. Botón Limpiar
clear_button = ttk.Button(
    right_frame,
    text="Limpiar", # Texto como en la imagen
    command=limpiar_campos, # Llama a la nueva función
    style='Secondary.TButton'
)
clear_button.grid(row=2, column=0, sticky="ew", pady=(0, 5)) # Se expande horizontalmente

# --- Iniciar y estado inicial ---
if not picamera2_available:
     actualizar_estado("Error: picamera2 no disponible. Botón deshabilitado.", error=True)
else:
     actualizar_estado("Listo.", info=True) # Mensaje inicial en el área de texto


root.mainloop()