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
last_photo_path = None

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

    clear_button.config(state=tk.DISABLED)
    actualizar_estado("Iniciando cámara...", info=True)
    root.update_idletasks()
    picam2 = None
    success = False
    try:
        picam2 = Picamera2()
        save_dir = "fotos_capturadas"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"foto_{timestamp}.jpg"
        ruta_completa = os.path.join(save_dir, nombre_archivo)

        config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
        picam2.configure(config)
        picam2.start()

        actualizar_estado("Ajustando parámetros...", info=True); root.update_idletasks(); time.sleep(2)
        actualizar_estado(f"Capturando foto: {nombre_archivo}...", info=True); root.update_idletasks()

        metadata = picam2.capture_file(ruta_completa)
        print("Metadatos de captura:", metadata)

        last_photo_path = ruta_completa
        mostrar_imagen(ruta_completa) # Llama a la función actualizada
        actualizar_estado(f"Foto guardada en '{save_dir}/'\nMostrando previsualización.", success=True)
        take_photo_button.config(state=tk.DISABLED)
        success = True

    except Exception as e:
        mensaje_error = f"Error al tomar foto: {e}"; print(mensaje_error)
        actualizar_estado(mensaje_error, error=True)
        limpiar_imagen()
        take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)

    finally:
        if picam2 and picam2.started:
            picam2.stop(); picam2.close(); print("Cámara detenida y cerrada.")
            if success: actualizar_estado("(Cámara detenida)", append=True, info=True)
        clear_button.config(state=tk.NORMAL)


def mostrar_imagen(ruta_imagen):
    """Carga, redimensiona (maximizando sin distorsión) y muestra la imagen."""
    if not pillow_available: return
    try:
        # Abrir la imagen original
        img = Image.open(ruta_imagen)
        img_width, img_height = img.size

        # Obtener dimensiones del label (forzar actualización del layout)
        image_label.update_idletasks()
        label_width = image_label.winfo_width()
        label_height = image_label.winfo_height()

        # Si el label aún no tiene tamaño, usar uno por defecto grande
        if label_width <= 1 or label_height <= 1:
            label_width = 600 # Ajustar si es necesario
            label_height = 450

        # Calcular aspect ratios
        img_aspect = img_width / float(img_height)
        label_aspect = label_width / float(label_height)

        # Dejar un pequeño margen (opcional)
        target_width = label_width - 10
        target_height = label_height - 10

        # Determinar dimensiones de redimensionamiento para llenar el espacio sin distorsión
        if img_aspect > label_aspect:
            # La imagen es más ancha (relativamente) que el label -> ajustar al ancho del label
            new_width = int(target_width)
            new_height = int(new_width / img_aspect)
        else:
            # La imagen es más alta (relativamente) o igual -> ajustar al alto del label
            new_height = int(target_height)
            new_width = int(new_height * img_aspect)

        # Asegurarse que las dimensiones no sean cero o negativas
        if new_width <= 0 : new_width = 1
        if new_height <= 0 : new_height = 1

        # Redimensionar usando el método resize (LANCZOS es alta calidad)
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convertir a formato Tkinter
        photo = ImageTk.PhotoImage(resized_img)

        # Mostrar en el label
        image_label.configure(image=photo, text="") # Quitar texto placeholder
        image_label.image = photo # Guardar referencia

    except FileNotFoundError:
         print(f"Error: No se encontró el archivo de imagen: {ruta_imagen}")
         actualizar_estado(f"Error: Archivo no encontrado {os.path.basename(ruta_imagen)}", error=True, append=True)
         limpiar_imagen()
    except Exception as e:
        print(f"Error al mostrar imagen: {e}")
        actualizar_estado(f"Error al mostrar imagen: {e}", error=True, append=True)
        limpiar_imagen()


def limpiar_campos():
    """Limpia campos, borra archivo y REHABILITA botón 'Foto'."""
    global last_photo_path

    if not last_photo_path and not text_area.get("1.0", tk.END).strip().startswith("Listo."):
        # Si no hay foto Y el texto no es solo el mensaje "Listo", preguntar.
         pass # Continuar para limpiar el texto
    elif not last_photo_path:
        actualizar_estado("Nada que limpiar.", info=True)
        return # No hay foto Y el texto está limpio, salir.


    confirmar = messagebox.askyesno("Confirmar Limpieza",
                                    "¿Limpiar campos y borrar la última foto del disco?")
    if not confirmar:
        actualizar_estado("Limpieza cancelada.", info=True)
        return

    # Limpiar texto
    text_area.delete('1.0', tk.END)
    text_area.insert('1.0', "Listo. Campos limpiados.")
    text_area.tag_remove(tk.ALL, "1.0", tk.END)
    text_area.tag_add("info", "1.0", tk.END)

    # Limpiar imagen
    limpiar_imagen()

    # Borrar archivo
    deleted_msg = ""
    path_to_delete = last_photo_path
    if path_to_delete:
        if os.path.exists(path_to_delete):
            try:
                os.remove(path_to_delete); print(f"Archivo eliminado: {path_to_delete}")
                deleted_msg = f"\nArchivo '{os.path.basename(path_to_delete)}' eliminado."
                last_photo_path = None # Éxito
            except Exception as e:
                print(f"Error al borrar {path_to_delete}: {e}")
                deleted_msg = f"\nError al borrar {os.path.basename(path_to_delete)}: {e}"
        else:
            print(f"Advertencia: {path_to_delete} ya no existía.")
            deleted_msg = f"\nAdvertencia: {os.path.basename(path_to_delete)} ya no existía."
            last_photo_path = None # No existe, resetear
    else:
        deleted_msg = "\n(No había foto registrada para borrar)."

    # Habilitar botón Foto
    take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)

    # Estado final
    actualizar_estado(deleted_msg, append=True, info=("Error" not in deleted_msg and "Advertencia" not in deleted_msg), error=("Error" in deleted_msg))


def limpiar_imagen():
    """Quita la imagen del label."""
    if not pillow_available: return
    image_label.configure(image=None, text="Imagen capturada aparecerá aquí", font=placeholder_font_style) # Asegurar fuente placeholder
    image_label.image = None

# Función actualizar_estado sin cambios lógicos internos
def actualizar_estado(mensaje, error=False, success=False, info=False, append=False):
    """Actualiza el texto y color en el área de texto."""
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
    end_index = text_area.index(tk.END + "-1c")

    if tag_to_apply:
         current_content = text_area.get("1.0", tk.END)
         if text_area.compare(start_index, ">=", "1.0") and \
            text_area.compare(start_index, "<", end_index):
              text_area.tag_add(tag_to_apply, start_index, end_index)

    if not text_area.get(end_index) == '\n': # Asegurar newline al final
         text_area.insert(tk.END, "\n")

    text_area.see(tk.END)


# --- Configuración de la Interfaz Gráfica ---

root = tk.Tk()
root.title("Capturadora Raspberry Pi")
# Aumentar tamaño ventana para fuentes más grandes
root.geometry("900x600")

# --- Paleta de Colores (sin cambios) ---
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

# --- Fuentes MÁS GRANDES ---
default_font_family = "Helvetica" # O "Arial", "Verdana"
button_font_size = 13
text_area_font_size = 12
placeholder_font_size = 15

button_font_style = font.Font(family=default_font_family, size=button_font_size, weight='bold')
text_area_font_style = font.Font(family=default_font_family, size=text_area_font_size)
# Fuente para el texto placeholder de la imagen (italic)
placeholder_font_style = font.Font(family=default_font_family, size=placeholder_font_size, slant='italic')


# --- Estilos ttk (aplicando nuevas fuentes) ---
style = Style(root)
style.theme_use('clam')

# Botones con fuente más grande y padding ajustado si es necesario
style.configure('TButton', font=button_font_style, padding=(12, 6)) # Aumentar padding
style.map('TButton', foreground=[('disabled', '#adb5bd')], background=[('disabled', '#e9ecef')])
style.configure('Primary.TButton', background=COLOR_PRIMARY, foreground=COLOR_BTN_FG)
style.map('Primary.TButton', background=[('active', '#0056b3'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])
style.configure('Secondary.TButton', background=COLOR_SECONDARY, foreground=COLOR_BTN_FG)
style.map('Secondary.TButton', background=[('active', '#5a6268'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])

# Frames y Label Placeholder
style.configure('TFrame', background=COLOR_BG)
style.configure('ImagePlaceholder.TLabel',
                background=COLOR_PLACEHOLDER_BG,
                foreground=COLOR_SECONDARY,
                font=placeholder_font_style, # Aplicar fuente placeholder
                anchor=tk.CENTER,
                relief=tk.SOLID,
                borderwidth=1)

# --- Layout con Grid (sin cambios estructurales) ---
main_frame = ttk.Frame(root, padding="15 15 15 15", style='TFrame') # Mayor padding general
main_frame.pack(fill=tk.BOTH, expand=True)

main_frame.columnconfigure(0, weight=3) # Imagen más espacio
main_frame.columnconfigure(1, weight=1) # Controles menos espacio
main_frame.rowconfigure(0, weight=1)

# Columna Izquierda (Imagen)
image_label = ttk.Label(main_frame,
                        text="Imagen capturada aparecerá aquí",
                        style='ImagePlaceholder.TLabel')
image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0) # Más padding a la derecha

# Columna Derecha (Controles)
right_frame = ttk.Frame(main_frame, style='TFrame', padding=(10, 0)) # Más padding izquierdo
right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
right_frame.rowconfigure(0, weight=3) # Text Area
right_frame.rowconfigure(1, weight=0) # Boton Foto
right_frame.rowconfigure(2, weight=0) # Boton Limpiar
right_frame.columnconfigure(0, weight=1)
right_frame.columnconfigure(1, weight=0)

# Campo de Texto (con fuente más grande)
text_area = tk.Text(right_frame, height=10, width=30, wrap=tk.WORD,
                    font=text_area_font_style, # Aplicar fuente texto
                    relief=tk.SOLID, borderwidth=1, fg=COLOR_FG, bg="white")
text_area.grid(row=0, column=0, sticky="nsew", pady=(0, 15)) # Más padding abajo
scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=text_area.yview)
scrollbar.grid(row=0, column=1, sticky='ns', pady=(0, 15))
text_area['yscrollcommand'] = scrollbar.set

# Botones (usarán estilo TButton con fuente grande)
take_photo_button = ttk.Button(right_frame, text="Foto", command=tomar_foto, style='Primary.TButton')
take_photo_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8) # Más padding vertical

clear_button = ttk.Button(right_frame, text="Limpiar", command=limpiar_campos, style='Secondary.TButton')
clear_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8)) # Más padding vertical

# --- Iniciar y estado inicial (lógica sin cambios) ---
initial_message = "Listo."
error_message = ""
can_take_photo = True
if not picamera2_available: error_message += "Error: picamera2 no disponible.\n"; can_take_photo = False
if not pillow_available: error_message += "Error: Pillow (PIL/ImageTk) no disponible.\n"; can_take_photo = False

if error_message:
    actualizar_estado(error_message + "Funcionalidad limitada.", error=True)
    take_photo_button.config(state=tk.DISABLED)
else:
     actualizar_estado(initial_message, info=True)
     take_photo_button.config(state=tk.NORMAL)

root.mainloop()