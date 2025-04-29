import tkinter as tk
from tkinter import ttk, font, messagebox
from tkinter.ttk import Style
import time
from datetime import datetime
import os
import logging
try:
    from PIL import Image, ImageTk
    pillow_available = True
except ImportError:
    print("Error: Pillow o ImageTk no encontrado.")
    print("Por favor, instala con: sudo apt update && sudo apt install python3-pil python3-pil.imagetk")
    pillow_available = False

# --- Configuración de Logging ---
# logging.basicConfig(level=logging.INFO)

# --- Comprobación de Picamera2 ---
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
last_photo_path = None # Ruta de la foto actualmente mostrada/guardada

# --- Funciones ---

def tomar_foto():
    """Captura una foto, la muestra, actualiza estado y DESHABILITA el botón 'Foto'."""
    global last_photo_path
    if not picamera2_available:
        actualizar_estado("Error: picamera2 no disponible.", error=True)
        return
    if not pillow_available:
        actualizar_estado("Error: Pillow (PIL) no disponible para mostrar imagen.", error=True)
        return

    # Aunque se deshabilita al final, es buena práctica deshabilitar durante la operación
    # take_photo_button.config(state=tk.DISABLED) # Se deshabilita permanentemente al final si tiene éxito
    clear_button.config(state=tk.DISABLED) # Deshabilitar limpiar durante captura
    actualizar_estado("Iniciando cámara...", info=True)
    root.update_idletasks()
    picam2 = None
    success = False # Flag para saber si la operación fue exitosa
    try:
        picam2 = Picamera2()
        # Directorio para guardar fotos
        save_dir = "fotos_capturadas"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Generar nombre y ruta ANTES de la captura
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"foto_{timestamp}.jpg"
        ruta_completa = os.path.join(save_dir, nombre_archivo)

        # Configurar cámara
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

        actualizar_estado(f"Capturando foto: {nombre_archivo}...", info=True)
        root.update_idletasks()

        # Capturar
        metadata = picam2.capture_file(ruta_completa)
        print("Metadatos de captura:", metadata)

        # *** Solo si la captura fue exitosa ***
        last_photo_path = ruta_completa # Actualizar la ruta de la última foto válida
        mostrar_imagen(ruta_completa)
        actualizar_estado(f"Foto guardada en '{save_dir}/'\nMostrando previsualización.", success=True)
        take_photo_button.config(state=tk.DISABLED) # <-- DESHABILITAR BOTÓN FOTO AQUÍ
        success = True # Marcar como éxito

    except Exception as e:
        mensaje_error = f"Error al tomar foto: {e}"
        print(mensaje_error)
        actualizar_estado(mensaje_error, error=True)
        # Si falla, no actualizamos last_photo_path y limpiamos la imagen
        limpiar_imagen()
        # Asegurarse que el botón de foto quede habilitado si falló (siempre que el hw esté ok)
        take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)


    finally:
        if picam2 and picam2.started:
            picam2.stop()
            picam2.close()
            print("Cámara detenida y cerrada.")
            if success: # Solo añadir mensaje si no hubo error antes
                 actualizar_estado("(Cámara detenida)", append=True, info=True)
        # Siempre reactivar Limpiar al final (si tuvo éxito o falló)
        clear_button.config(state=tk.NORMAL)


def mostrar_imagen(ruta_imagen):
    """Carga y muestra la imagen en el image_label."""
    if not pillow_available: return
    try:
        img = Image.open(ruta_imagen)
        image_label.update_idletasks()
        label_width = image_label.winfo_width()
        label_height = image_label.winfo_height()

        if label_width < 1 or label_height < 1: label_width, label_height = 400, 300

        img.thumbnail((label_width - 10, label_height - 10), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        image_label.configure(image=photo, text="")
        image_label.image = photo

    except Exception as e:
        print(f"Error al mostrar imagen: {e}")
        actualizar_estado(f"Error al mostrar imagen: {e}", error=True, append=True)
        limpiar_imagen()
        # Si falla la muestra, quizás habilitar botón foto de nuevo? Opcional.
        # take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)


def limpiar_campos():
    """Limpia campos, borra archivo de última foto y REHABILITA el botón 'Foto'."""
    global last_photo_path

    # No pedir confirmación si no hay foto que borrar/limpiar
    if not last_photo_path and not text_area.get("1.0", tk.END).strip():
        actualizar_estado("Nada que limpiar.", info=True)
        return

    confirmar = messagebox.askyesno("Confirmar Limpieza",
                                    "¿Limpiar campos y borrar la última foto del disco?")
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

    # 3. Borrar el archivo de la última foto guardada (la que estaba mostrándose)
    deleted_msg = ""
    path_to_delete = last_photo_path # Guardar la ruta antes de resetearla
    if path_to_delete:
        if os.path.exists(path_to_delete):
            try:
                os.remove(path_to_delete)
                print(f"Archivo eliminado: {path_to_delete}")
                deleted_msg = f"\nArchivo '{os.path.basename(path_to_delete)}' eliminado."
                last_photo_path = None # Resetear AHORA, después de borrar con éxito

            except Exception as e:
                print(f"Error al borrar el archivo {path_to_delete}: {e}")
                deleted_msg = f"\nError al borrar {os.path.basename(path_to_delete)}: {e}"
                # No reseteamos last_photo_path si falla el borrado, podría intentarse de nuevo
        else:
            print(f"Advertencia: El archivo {path_to_delete} ya no existía.")
            deleted_msg = f"\nAdvertencia: {os.path.basename(path_to_delete)} ya no existía."
            last_photo_path = None # El archivo no está, así que reseteamos la variable
    else:
        deleted_msg = "\n(No había foto registrada para borrar)."

    # 4. REHABILITAR el botón de tomar foto (si el hardware está disponible)
    take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)

    # Actualizar estado final de la limpieza
    actualizar_estado(deleted_msg, append=True, info=("Error" not in deleted_msg and "Advertencia" not in deleted_msg), error=("Error" in deleted_msg))


def limpiar_imagen():
    """Quita la imagen del label."""
    if not pillow_available: return
    image_label.configure(image=None, text="Imagen capturada aparecerá aquí")
    image_label.image = None

def actualizar_estado(mensaje, error=False, success=False, info=False, append=False):
    """Actualiza el texto y color en el área de texto."""
    # Configurar tags si no existen
    tags = {"error": COLOR_ERROR, "success": COLOR_SUCCESS, "info": COLOR_INFO}
    for tag_name, color in tags.items():
        if tag_name not in text_area.tag_names():
            text_area.tag_configure(tag_name, foreground=color)

    tag_to_apply = None
    if error: tag_to_apply = "error"
    elif success: tag_to_apply = "success"
    elif info: tag_to_apply = "info"

    start_index = "1.0"
    if not append:
        text_area.delete("1.0", tk.END)
    else:
        if text_area.get("end-2c", "end-1c") != '\n':
             text_area.insert(tk.END, "\n")
        start_index = text_area.index(tk.END + "-1c")

    text_area.insert(tk.END, mensaje)
    end_index = text_area.index(tk.END + "-1c") # Index before the final newline Tkinter adds

    # Apply tag only to the newly added text
    if tag_to_apply:
        # Ensure start_index is valid before tagging
        current_content = text_area.get("1.0", tk.END)
        if text_area.compare(start_index, ">=", "1.0") and \
           text_area.compare(start_index, "<", end_index):
             text_area.tag_add(tag_to_apply, start_index, end_index)
        elif text_area.compare(start_index, "==", end_index): # Handle empty message case or single char
             pass # Nothing to tag or already tagged
        # else: print(f"Debug: Invalid index range for tag: {start_index} to {end_index}")


    if not mensaje.endswith('\n'):
        text_area.insert(tk.END, "\n")

    text_area.see(tk.END)


# --- Configuración de la Interfaz Gráfica (sin cambios en widgets, estilos, layout) ---

root = tk.Tk()
root.title("Capturadora Raspberry Pi")
root.geometry("800x450")

# Paleta de Colores y Fuentes (sin cambios)
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

# Estilos ttk (sin cambios)
style = Style(root)
style.theme_use('clam')
# ... (definiciones de style.configure y style.map iguales que antes) ...
style.configure('TButton', font=button_font_style, padding=(10, 5), borderwidth=1)
style.map('TButton', foreground=[('disabled', '#adb5bd')], background=[('disabled', '#e9ecef')])
style.configure('Primary.TButton', background=COLOR_PRIMARY, foreground=COLOR_BTN_FG)
style.map('Primary.TButton', background=[('active', '#0056b3'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])
style.configure('Secondary.TButton', background=COLOR_SECONDARY, foreground=COLOR_BTN_FG)
style.map('Secondary.TButton', background=[('active', '#5a6268'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])
style.configure('TFrame', background=COLOR_BG)
style.configure('ImagePlaceholder.TLabel', background=COLOR_PLACEHOLDER_BG, foreground=COLOR_SECONDARY, font=placeholder_font_style, anchor=tk.CENTER, relief=tk.SOLID, borderwidth=1)


# Layout con Grid (sin cambios)
main_frame = ttk.Frame(root, padding="10 10 10 10", style='TFrame')
main_frame.pack(fill=tk.BOTH, expand=True)
main_frame.columnconfigure(0, weight=3)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(0, weight=1)

# Columna Izquierda (Imagen)
image_label = ttk.Label(main_frame, text="Imagen capturada aparecerá aquí", style='ImagePlaceholder.TLabel')
image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

# Columna Derecha (Controles)
right_frame = ttk.Frame(main_frame, style='TFrame', padding=(5, 0))
right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
right_frame.rowconfigure(0, weight=3)
right_frame.rowconfigure(1, weight=0)
right_frame.rowconfigure(2, weight=0)
right_frame.columnconfigure(0, weight=1)
right_frame.columnconfigure(1, weight=0) # Columna para scrollbar

# Campo de Texto y Scrollbar
text_area = tk.Text(right_frame, height=10, width=30, wrap=tk.WORD, font=text_area_font_style, relief=tk.SOLID, borderwidth=1, fg=COLOR_FG, bg="white")
text_area.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=text_area.yview)
scrollbar.grid(row=0, column=1, sticky='ns', pady=(0, 10))
text_area['yscrollcommand'] = scrollbar.set

# Botón Tomar Foto
take_photo_button = ttk.Button(right_frame, text="Foto", command=tomar_foto, style='Primary.TButton')
take_photo_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

# Botón Limpiar
clear_button = ttk.Button(right_frame, text="Limpiar", command=limpiar_campos, style='Secondary.TButton')
clear_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 5))

# --- Iniciar y estado inicial ---
initial_message = "Listo."
error_message = ""
can_take_photo = True # Asumimos que sí al principio

if not picamera2_available:
    error_message += "Error: picamera2 no disponible.\n"
    can_take_photo = False
if not pillow_available:
    error_message += "Error: Pillow (PIL/ImageTk) no disponible.\n"
    can_take_photo = False

if error_message:
    actualizar_estado(error_message + "Funcionalidad limitada.", error=True)
    take_photo_button.config(state=tk.DISABLED)
    # Considerar deshabilitar Limpiar también si no hay nada que limpiar inicialmente
    # clear_button.config(state=tk.DISABLED)
else:
     actualizar_estado(initial_message, info=True)
     # Estado inicial habilitado si todo está bien
     take_photo_button.config(state=tk.NORMAL)


root.mainloop()