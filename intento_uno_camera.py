import tkinter as tk
from tkinter import font
import time
from datetime import datetime
import os
import logging

# Configura el logging para ver mensajes de picamera2 si es necesario
# logging.basicConfig(level=logging.INFO)

try:
    # Intenta importar Picamera2. Fallará si no está instalado o si hay problemas.
    from picamera2 import Picamera2, Preview
    picamera2_available = True
except ImportError:
    print("Error: La biblioteca picamera2 no se encontró.")
    print("Por favor, instálala con: sudo apt install python3-picamera2")
    picamera2_available = False
except Exception as e:
    # Captura otros posibles errores durante la importación/inicialización temprana
    # (por ejemplo, si libcamera no está funcionando correctamente)
    print(f"Error al inicializar la cámara: {e}")
    print("Asegúrate de que la cámara esté conectada y habilitada en raspi-config.")
    picamera2_available = False

# --- Funciones ---

def tomar_foto():
    """Captura una foto usando Picamera2 y la guarda con timestamp."""
    if not picamera2_available:
        actualizar_estado("Error: picamera2 no disponible.", error=True)
        return

    # Actualizar estado en la GUI
    actualizar_estado("Iniciando cámara...")
    root.update_idletasks() # Asegura que la GUI se actualice

    picam2 = None # Inicializa a None
    try:
        # 1. Crear instancia de Picamera2
        picam2 = Picamera2()

        # 2. Configurar la cámara para captura de imagen fija
        # Puedes ajustar la resolución aquí si es necesario
        config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
        # Usamos una configuración con 'lores' (baja resolución) por si quisiéramos añadir una preview más adelante
        # y 'main' para la captura de alta resolución.
        picam2.configure(config)

        # 3. Iniciar la cámara
        # picam2.start_preview(Preview.DRM, x=100, y=200, width=640, height=480) # Descomentar si quieres preview
        picam2.start()

        # 4. Dar tiempo a la cámara para ajustar (autoexposición, balance de blancos)
        actualizar_estado("Ajustando parámetros...")
        root.update_idletasks()
        time.sleep(2) # Espera 2 segundos

        # 5. Generar nombre de archivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"foto_{timestamp}.jpg"
        ruta_completa = os.path.join(os.getcwd(), nombre_archivo) # Guarda en el directorio actual

        # 6. Capturar y guardar la foto
        actualizar_estado(f"Capturando foto: {nombre_archivo}...")
        root.update_idletasks()

        # Metadata puede ser útil
        metadata = picam2.capture_file(ruta_completa)
        print("Metadatos de captura:", metadata) # Imprime en consola

        actualizar_estado(f"¡Foto guardada! -> {nombre_archivo}", error=False)

    except Exception as e:
        mensaje_error = f"Error al tomar foto: {e}"
        print(mensaje_error) # También imprime en consola para más detalles
        actualizar_estado(mensaje_error, error=True)

    finally:
        # 7. Detener la cámara SIEMPRE (incluso si hubo error)
        if picam2 and picam2.started:
            # picam2.stop_preview() # Si usaste preview
            picam2.stop()
            picam2.close() # Libera recursos
            actualizar_estado(status_label.cget("text") + "\nCámara detenida.", error=status_label.cget("fg") == "red")
            print("Cámara detenida y cerrada.")


def limpiar_estado():
    """Limpia el texto del campo de estado."""
    actualizar_estado("Listo.", error=False)

def actualizar_estado(mensaje, error=False):
    """Actualiza el texto y color del label de estado."""
    status_label.config(text=mensaje, fg="red" if error else "blue")

# --- Configuración de la Interfaz Gráfica (Tkinter) ---

root = tk.Tk()
root.title("Captura de Foto - Raspberry Pi")
root.geometry("450x200") # Tamaño inicial de la ventana

# Estilo de fuente
default_font = font.nametofont("TkDefaultFont")
default_font.configure(size=12)
button_font = font.Font(family='Helvetica', size=12, weight='bold')

# --- Widgets ---

# 1. Botón para tomar foto
take_photo_button = tk.Button(
    root,
    text="Tomar Foto",
    command=tomar_foto,
    font=button_font,
    bg="#4CAF50", # Verde
    fg="white",
    padx=10,
    pady=5,
    state=tk.NORMAL if picamera2_available else tk.DISABLED # Deshabilitar si no hay cámara
)
take_photo_button.pack(pady=15) # Añade espacio vertical

# 2. Campo (Label) para mostrar estado/mensajes
status_label = tk.Label(
    root,
    text="Haz clic en 'Tomar Foto'",
    bd=1, # Borde
    relief=tk.SUNKEN, # Apariencia hundida
    anchor=tk.W, # Alinear texto a la izquierda (West)
    padx=5,
    pady=5,
    font=('Helvetica', 10),
    wraplength=400 # Ancho máximo antes de saltar línea
)
status_label.pack(pady=10, fill=tk.X, padx=10) # Ocupa ancho, con padding

# 3. Botón para limpiar el estado
clear_button = tk.Button(
    root,
    text="Limpiar Mensaje",
    command=limpiar_estado,
    font=button_font,
    bg="#f44336", # Rojo
    fg="white",
    padx=10,
    pady=5
)
clear_button.pack(pady=5)

# --- Iniciar el bucle principal de Tkinter ---
if not picamera2_available:
     actualizar_estado("Error: picamera2 no disponible. Botón deshabilitado.", error=True)

root.mainloop()