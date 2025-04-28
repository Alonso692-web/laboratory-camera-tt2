import tkinter as tk
from tkinter import ttk, font, messagebox # Añadir messagebox para confirmación opcional
from tkinter.ttk import Style
import time
from datetime import datetime
import os
import logging
try:
    # Necesario para mostrar imágenes en Tkinter
    from PIL import Image, ImageTk
    pillow_available = True
except ImportError:
    print("Error: Pillow o ImageTk no encontrado.")
    print("Por favor, instala con: sudo apt update && sudo apt install python3-pil python3-pil.imagetk")
    pillow_available = False

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
    # Deshabilitar Pillow también si no hay cámara, para evitar errores si no se instaló
    # pillow_available = False
except Exception as e:
    print(f"Error al inicializar la cámara: {e}")
    print("Asegúrate de que la cámara esté conectada y habilitada en raspi-config.")
    picamera2_available = False
    # pillow_available = False

# --- Variables Globales ---
last_photo_path = None # Para guardar la ruta de la última foto tomada

# --- Funciones de Cámara, Visualización y Limpieza ---

def tomar_foto():
    """Captura una foto, la muestra y actualiza el estado."""
    global last_photo_path
    if not picamera2_available:
        actualizar_estado("Error: picamera2 no disponible.", error=True)
        return
    if not pillow_available:
        actualizar_estado("Error: Pillow (PIL) no disponible para mostrar imagen.", error=True)
        return

    # Deshabilitar botones mientras se procesa
    take_photo_button.config(state=tk.DISABLED)
    clear_button.config(state=tk.DISABLED)
    actualizar_estado("Iniciando cámara...", info=True)
    root.update_idletasks()
    picam2 = None
    try:
        picam2 = Picamera2()
        config = picam2.create_still_configuration(
            main={"size": (1920, 1080)},
            lores={"size": (640, 480)},
            display="lores"
        )
        picam2.configure(config)
        picam2.start()

        actualizar_estado("Ajustando parámetros...", info=True)
        root.update_idletasks()
        time.sleep(2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"foto_{timestamp}.jpg"
        # Guardar en un subdirectorio 'fotos' (opcional, pero más ordenado)
        save_dir = "fotos_capturadas"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        ruta_completa = os.path.join(save_dir, nombre_archivo)

        # Antes de guardar la nueva, si había una anterior *no limpiada*, borrarla (opcional)
        # if last_photo_path and os.path.exists(last_photo_path):
        #    try: os.remove(last_photo_path)
        #    except Exception as e_del: print(f"No se pudo borrar foto anterior {last_photo_path}: {e_del}")

        last_photo_path = ruta_completa # Guarda la ruta ANTES de capturar

        actualizar_estado(f"Capturando foto: {nombre_archivo}...", info=True)
        root.update_idletasks()

        metadata = picam2.capture_file(ruta_completa)
        print("Metadatos de captura:", metadata)

        mostrar_imagen(ruta_completa)
        actualizar_estado(f"Foto guardada en '{save_dir}/'\nMostrando previsualización.", success=True)

    except Exception as e:
        mensaje_error = f"Error al tomar foto: {e}"
        print(mensaje_error)
        actualizar_estado(mensaje_error, error=True)
        last_photo_path = None # Resetea si hubo error
        limpiar_imagen()

    finally:
        if picam2 and picam2.started:
            picam2.stop()
            picam2.close()
            print("Cámara detenida y cerrada.")
            current_text = text_area.get("1.0", tk.END).strip()
            if current_text:
                 actualizar_estado("(Cámara detenida)", append=True, info=True) # Usar info color
        # Reactivar botones
        take_photo_button.config(state=tk.NORMAL if picamera2_available else tk.DISABLED)
        clear_button.config(state=tk.NORMAL)


def mostrar_imagen(ruta_imagen):
    """Carga y muestra la imagen en el image_label."""
    if not pillow_available: return
    try:
        img = Image.open(ruta_imagen)
        image_label.update_idletasks()
        label_width = image_label.winfo_width()
        label_height = image_label.winfo_height()

        if label_width < 1 or label_height < 1:
             label_width = 400
             label_height = 300

        img.thumbnail((label_width - 10, label_height - 10), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        image_label.configure(image=photo, text="")
        image_label.image = photo

    except Exception as e:
        print(f"Error al mostrar imagen: {e}")
        actualizar_estado(f"Error al mostrar imagen: {e}", error=True, append=True)
        limpiar_imagen()

def limpiar_campos():
    """Limpia el área de texto, la imagen y **borra el archivo de la última foto**."""
    global last_photo_path

    confirmar = messagebox.askyesno("Confirmar Limpieza",
                                    "¿Estás seguro de que quieres limpiar los campos y borrar la última foto guardada del disco?")

    if not confirmar:
        actualizar_estado("Limpieza cancelada.", info=True)
        return

    # 1. Limpiar área de texto
    text_area.delete('1.0', tk.END)
    text_area.insert('1.0', "Listo. Campos limpiados.")
    text_area.tag_remove(tk.ALL, "1.0", tk.END)
    text_area.tag_add("info", "1.0", tk.END)

    # 2. Limpiar visualización de imagen
    limpiar_imagen()

    # 3. Borrar el archivo de la última foto tomada
    deleted_msg = ""
    if last_photo_path: # Solo intentar borrar si hay una ruta guardada
        if os.path.exists(last_photo_path):
            try:
                os.remove(last_photo_path)
                print(f"Archivo eliminado: {last_photo_path}")
                deleted_msg = f"\nArchivo '{os.path.basename(last_photo_path)}' eliminado."
                last_photo_path = None # ¡Importante! Resetear solo si se borró con éxito

            except FileNotFoundError:
                 # Raro si os.path.exists era True, pero por si acaso
                 print(f"Error: El archivo {last_photo_path} no se encontró al intentar borrar.")
                 deleted_msg = f"\nError: No se encontró {os.path.basename(last_photo_path)} para borrar."
                 # No reseteamos last_photo_path aquí, el estado es inconsistente
            except OSError as e:
                print(f"Error de OS al borrar el archivo {last_photo_path}: {e}")
                deleted_msg = f"\nError al borrar {os.path.basename(last_photo_path)}: {e}"
                 # No reseteamos last_photo_path
            except Exception as e:
                 print(f"Error inesperado al borrar el archivo {last_photo_path}: {e}")
                 deleted_msg = f"\nError inesperado al borrar {os.path.basename(last_photo_path)}."
                 # No reseteamos last_photo_path
        else:
            # La ruta existía en la variable, pero el archivo ya no está en disco
            print(f"Advertencia: El archivo {last_photo_path} ya no existía en el disco.")
            deleted_msg = f"\nAdvertencia: {os.path.basename(last_photo_path)} ya no existía."
            last_photo_path = None # Limpiamos la variable porque el archivo no está
    else:
        # No había ninguna foto registrada para borrar
        deleted_msg = "\n(No había foto reciente registrada para borrar)."


    # Actualizar estado final de la limpieza
    actualizar_estado(deleted_msg, append=True, info=(not "Error" in deleted_msg and not "Advertencia" in deleted_msg), error=("Error" in deleted_msg))


def limpiar_imagen():
    """Quita la imagen del label y pone el texto placeholder."""
    if not pillow_available: return
    image_label.configure(image=None, text="Imagen capturada aparecerá aquí")
    image_label.image = None

def actualizar_estado(mensaje, error=False, success=False, info=False, append=False):
    """Actualiza el texto y color en el área de texto."""
    # Definir tags de color (solo si no existen)
    if not "error" in text_area.tag_names():
        text_area.tag_configure("error", foreground=COLOR_ERROR)
    if not "success" in text_area.tag_names():
        text_area.tag_configure("success", foreground=COLOR_SUCCESS)
    if not "info" in text_area.tag_names():
        text_area.tag_configure("info", foreground=COLOR_INFO)

    tag = None
    if error: tag = "error"
    elif success: tag = "success"
    elif info: tag = "info"

    start_index = "1.0"
    if not append:
        text_area.delete("1.0", tk.END)
    else:
        # Si es append y el text area no termina ya con newline, añadir una.
        if text_area.get("end-2c", "end-1c") != '\n':
             text_area.insert(tk.END, "\n")
        start_index = text_area.index(tk.END + "-1c")


    text_area.insert(tk.END, mensaje)
    end_index = text_area.index(tk.END + "-1c")

    if tag:
        text_area.tag_add(tag, start_index, end_index)

    # Añadir newline al final si el mensaje no lo tenía, para el siguiente append
    if not mensaje.endswith('\n'):
        text_area.insert(tk.END, "\n")


    text_area.see(tk.END)


# --- Configuración de la Interfaz Gráfica (Tkinter + ttk + grid) ---
# (Sin cambios en la definición de la GUI, colores, estilos y layout)

root = tk.Tk()
root.title("Capturadora Raspberry Pi")
root.geometry("800x450")

# --- Paleta de Colores y Fuentes ---
COLOR_PRIMARY = "#007bff"
COLOR_SECONDARY = "#6c757d"
COLOR_SUCCESS = "#28a745"
COLOR_ERROR = "#dc3545"
COLOR_INFO = "#17a2b8"
COLOR_BG = "#f8f9fa"
COLOR_FG = "#212529"
COLOR_BTN_FG = "#ffffff"
COLOR_PLACEHOLDER_BG = "#e9ecef"

root.configure(bg=COLOR_BG)

default_font_family = "Helvetica"
button_font_style = font.Font(family=default_font_family, size=11, weight='bold')
text_area_font_style = font.Font(family=default_font_family, size=10)
placeholder_font_style = font.Font(family=default_font_family, size=12, slant='italic')

# --- Estilos ttk ---
style = Style(root)
style.theme_use('clam')

style.configure('TButton', font=button_font_style, padding=(10, 5), borderwidth=1)
style.map('TButton', foreground=[('disabled', '#adb5bd')], background=[('disabled', '#e9ecef')])

style.configure('Primary.TButton', background=COLOR_PRIMARY, foreground=COLOR_BTN_FG)
style.map('Primary.TButton', background=[('active', '#0056b3'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])

style.configure('Secondary.TButton', background=COLOR_SECONDARY, foreground=COLOR_BTN_FG)
style.map('Secondary.TButton', background=[('active', '#5a6268'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])

style.configure('TFrame', background=COLOR_BG)

style.configure('ImagePlaceholder.TLabel',
                background=COLOR_PLACEHOLDER_BG,
                foreground=COLOR_SECONDARY,
                font=placeholder_font_style,
                anchor=tk.CENTER,
                relief=tk.SOLID,
                borderwidth=1)

# --- Layout con Grid ---
main_frame = ttk.Frame(root, padding="10 10 10 10", style='TFrame')
main_frame.pack(fill=tk.BOTH, expand=True)

main_frame.columnconfigure(0, weight=3)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(0, weight=1)

# --- Columna Izquierda (Imagen) ---
image_label = ttk.Label(main_frame,
                        text="Imagen capturada aparecerá aquí",
                        style='ImagePlaceholder.TLabel')
image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

# --- Columna Derecha (Controles) ---
right_frame = ttk.Frame(main_frame, style='TFrame', padding=(5, 0))
right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

right_frame.rowconfigure(0, weight=3)
right_frame.rowconfigure(1, weight=0)
right_frame.rowconfigure(2, weight=0)
right_frame.columnconfigure(0, weight=1)

# 1. Campo de Texto (tk.Text)
text_area = tk.Text(right_frame,
                    height=10,
                    width=30,
                    wrap=tk.WORD,
                    font=text_area_font_style,
                    relief=tk.SOLID,
                    borderwidth=1,
                    fg=COLOR_FG,
                    bg="white") # Fondo blanco para diferenciarlo
text_area.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

# Scrollbar para el Text widget
scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=text_area.yview)
scrollbar.grid(row=0, column=1, sticky='ns', pady=(0, 10))
text_area['yscrollcommand'] = scrollbar.set

# 2. Botón Tomar Foto
take_photo_button = ttk.Button(
    right_frame,
    text="Foto",
    command=tomar_foto,
    style='Primary.TButton',
    state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED
)
take_photo_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5) # columnspan=2

# 3. Botón Limpiar
clear_button = ttk.Button(
    right_frame,
    text="Limpiar",
    command=limpiar_campos,
    style='Secondary.TButton'
)
clear_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 5)) # columnspan=2

# --- Iniciar y estado inicial ---
initial_message = "Listo."
error_message = ""
if not picamera2_available:
    error_message += "Error: picamera2 no disponible.\n"
if not pillow_available:
    error_message += "Error: Pillow (PIL/ImageTk) no disponible.\n"

if error_message:
    actualizar_estado(error_message + "Funcionalidad limitada.", error=True)
else:
     actualizar_estado(initial_message, info=True)


root.mainloop()