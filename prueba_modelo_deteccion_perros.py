import tkinter as tk
from tkinter import ttk, font, messagebox
from tkinter.ttk import Style
import time
from datetime import datetime
import os
import logging
import numpy as np # Para manipulación numérica (requerido por TF)

# --- Pillow (PIL) ---
try:
    from PIL import Image, ImageTk
    pillow_available = True
except ImportError:
    print("Error: Pillow o ImageTk no encontrado.")
    print("Por favor, instala con: sudo apt update && sudo apt install python3-pil python3-pil.imagetk")
    pillow_available = False

# --- TensorFlow / Keras ---
try:
    import tensorflow as tf
    # Específicamente las partes que usaremos
    from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
    from tensorflow.keras.preprocessing import image as keras_image # Renombrar para evitar conflicto con PIL.Image
    tf_available = True
    print(f"TensorFlow version: {tf.__version__}")
except ImportError:
    print("--------------------------------------------------")
    print("Error: TensorFlow no encontrado.")
    print("Instálalo con: pip install tensorflow")
    print("Puede requerir dependencias del sistema en Raspberry Pi.")
    print("La clasificación de imágenes estará deshabilitada.")
    print("--------------------------------------------------")
    tf_available = False
except Exception as e:
    print(f"Error al importar TensorFlow: {e}")
    tf_available = False


# --- Picamera2 ---
try:
    from picamera2 import Picamera2
    picamera2_available = True
except ImportError:
    print("Error: picamera2 no disponible.")
    picamera2_available = False
except Exception as e:
    print(f"Error al inicializar la cámara: {e}")
    picamera2_available = False

# --- Variables Globales ---
last_photo_path = None
model = None # Variable global para el modelo cargado

# --- Funciones ---

def cargar_modelo():
    """Carga el modelo MobileNetV2 pre-entrenado."""
    global model
    if not tf_available:
        print("TensorFlow no disponible, no se puede cargar el modelo.")
        return False
    if model is None: # Cargar solo si no está cargado ya
        try:
            print("Cargando modelo MobileNetV2 (puede tardar la primera vez)...")
            # input_shape=(224, 224, 3) es el tamaño estándar para MobileNetV2
            model = MobileNetV2(weights='imagenet', input_shape=(224, 224, 3))
            print("Modelo MobileNetV2 cargado exitosamente.")
            # Hacer una predicción dummy para "calentar" el modelo si es necesario
            # dummy_img = np.zeros((1, 224, 224, 3))
            # model.predict(dummy_img)
            # print("Modelo 'calentado'.")
            return True
        except Exception as e:
            print(f"Error crítico al cargar el modelo MobileNetV2: {e}")
            actualizar_estado(f"Error al cargar modelo IA: {e}", error=True, append=True)
            model = None # Asegurar que quede como None si falla
            return False
    return True # Ya estaba cargado

def preprocesar_imagen_tf(img_path):
    """Carga y preprocesa la imagen para MobileNetV2."""
    if not tf_available or not pillow_available: return None
    try:
        # Cargar imagen y asegurar tamaño 224x224
        img = keras_image.load_img(img_path, target_size=(224, 224))
        # Convertir a array numpy
        img_array = keras_image.img_to_array(img)
        # Expandir dimensiones para que sea (1, 224, 224, 3) -> un batch de 1 imagen
        img_array_expanded = np.expand_dims(img_array, axis=0)
        # Aplicar preprocesamiento específico de MobileNetV2 (normaliza píxeles)
        return preprocess_input(img_array_expanded)
    except Exception as e:
        print(f"Error al preprocesar imagen para TF: {e}")
        return None

def clasificar_imagen(img_path):
    """Clasifica la imagen usando el modelo cargado y busca perros/gatos."""
    if model is None or not tf_available:
        return "Modelo IA no cargado."

    processed_img = preprocesar_imagen_tf(img_path)
    if processed_img is None:
        return "Error al preprocesar imagen para IA."

    try:
        # Realizar la predicción
        predictions = model.predict(processed_img)
        # Decodificar las predicciones (top 3)
        # decode_predictions da [(class_id, class_name, probability), ...]
        decoded = decode_predictions(predictions, top=3)[0]
        print("Predicciones IA:", decoded)

        # Buscar 'cat' o 'dog' en las etiquetas de las top predicciones
        resultado = "No se detectó Perro/Gato"
        detected = False
        for _, label, prob in decoded:
            label_lower = label.lower()
            # ImageNet tiene muchas razas, buscar 'cat' o 'dog' es un inicio
            if 'cat' in label_lower:
                 # Añadir más términos si es necesario: 'feline', 'lynx', etc.
                 resultado = f"Detectado: Gato ({label}, {prob:.2%})"
                 detected = True
                 break # Quedarse con la primera detección
            elif 'dog' in label_lower:
                 # Añadir más términos: 'hound', 'terrier', 'canine', etc.
                 resultado = f"Detectado: Perro ({label}, {prob:.2%})"
                 detected = True
                 break

        if not detected:
             # Si no se detectó perro/gato, mostrar la predicción principal
             top_pred_label = decoded[0][1]
             top_pred_prob = decoded[0][2]
             resultado = f"Detectado: {top_pred_label} ({top_pred_prob:.2%})"

        return resultado

    except Exception as e:
        print(f"Error durante la clasificación: {e}")
        return "Error durante la clasificación IA."


def tomar_foto():
    """Captura, guarda, muestra, CLASIFICA y deshabilita botón."""
    global last_photo_path
    if not picamera2_available:
        actualizar_estado("Error: picamera2 no disponible.", error=True)
        return
    if not pillow_available:
        actualizar_estado("Error: Pillow no disponible.", error=True)
        return

    # Asegurarse que el modelo esté cargado antes de intentar tomar foto para clasificar
    if not cargar_modelo() and tf_available: # Solo fallar si TF debía estar disponible
        actualizar_estado("Fallo al cargar modelo IA. No se puede clasificar.", error=True)
        # Decidir si permitir tomar foto sin clasificar o no
        # return # Descomentar para impedir tomar foto si el modelo no carga

    clear_button.config(state=tk.DISABLED)
    take_photo_button.config(state=tk.DISABLED) # Deshabilitar mientras procesa
    actualizar_estado("Iniciando cámara...", info=True)
    root.update_idletasks()
    picam2 = None
    success = False
    clasificacion_result = "(Clasificación no disponible)"

    try:
        picam2 = Picamera2()
        save_dir = "fotos_capturadas"
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"foto_{timestamp}.jpg"
        ruta_completa = os.path.join(save_dir, nombre_archivo)

        config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
        picam2.configure(config)
        picam2.start()

        actualizar_estado("Ajustando...", info=True); root.update_idletasks(); time.sleep(1.5) # Menos tiempo
        actualizar_estado(f"Capturando: {nombre_archivo}...", info=True); root.update_idletasks()

        metadata = picam2.capture_file(ruta_completa)
        print("Metadatos:", metadata)

        # --- Mostrar y Clasificar ---
        last_photo_path = ruta_completa
        mostrar_imagen(ruta_completa) # Mostrar primero

        actualizar_estado(f"Foto guardada.\nClasificando...", info=True)
        root.update_idletasks() # Mostrar mensaje antes de clasificar

        if tf_available and model:
             clasificacion_result = clasificar_imagen(ruta_completa)
             print(f"Resultado clasificación: {clasificacion_result}")
        elif not tf_available:
             clasificacion_result = "(TensorFlow no instalado)"
        else: # TF disponible pero modelo no cargó
             clasificacion_result = "(Modelo IA no cargado)"

        # Actualizar estado final con resultado de clasificación
        actualizar_estado(f"Previsualización mostrada.\n{clasificacion_result}", success=True)

        # Deshabilitar botón permanentemente hasta limpiar
        # take_photo_button.config(state=tk.DISABLED) # Ya está deshabilitado desde el inicio de la función
        success = True

    except Exception as e:
        mensaje_error = f"Error en toma/clasificación: {e}"; print(mensaje_error)
        actualizar_estado(mensaje_error, error=True)
        limpiar_imagen()
        # Habilitar botón foto solo si el error no fue fatal (permite reintentar)
        take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)

    finally:
        if picam2 and picam2.started:
            picam2.stop(); picam2.close(); print("Cámara detenida.")
            # No añadir mensaje extra si ya hay resultado o error
        # Reactivar Limpiar siempre
        clear_button.config(state=tk.NORMAL)
        # El botón Tomar Foto queda deshabilitado si success=True


# --- Funciones mostrar_imagen, limpiar_campos, limpiar_imagen, actualizar_estado (sin cambios lógicos internos, solo asegurar que se llamen correctamente) ---
# (Incluyo mostrar_imagen por si acaso)
def mostrar_imagen(ruta_imagen):
    """Carga, redimensiona (maximizando sin distorsión) y muestra la imagen."""
    if not pillow_available: return
    try:
        img = Image.open(ruta_imagen)
        img_width, img_height = img.size
        image_label.update_idletasks()
        label_width = image_label.winfo_width()
        label_height = image_label.winfo_height()
        if label_width <= 1 or label_height <= 1: label_width, label_height = 600, 450

        img_aspect = img_width / float(img_height)
        label_aspect = label_width / float(label_height)
        target_width = label_width - 10
        target_height = label_height - 10

        if img_aspect > label_aspect:
            new_width = int(target_width)
            new_height = int(new_width / img_aspect)
        else:
            new_height = int(target_height)
            new_width = int(new_height * img_aspect)

        if new_width <= 0 : new_width = 1
        if new_height <= 0 : new_height = 1

        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized_img)
        image_label.configure(image=photo, text="")
        image_label.image = photo
    except FileNotFoundError:
         print(f"Error: No se encontró: {ruta_imagen}")
         actualizar_estado(f"Error: Archivo no encontrado {os.path.basename(ruta_imagen)}", error=True, append=True)
         limpiar_imagen()
    except Exception as e:
        print(f"Error al mostrar imagen: {e}")
        actualizar_estado(f"Error al mostrar imagen: {e}", error=True, append=True)
        limpiar_imagen()


def limpiar_campos():
    """Limpia campos, borra archivo y REHABILITA botón 'Foto'."""
    global last_photo_path
    path_to_delete = last_photo_path # Guardar antes de preguntar/resetear
    confirm = True # Asumir sí por defecto si no hay nada crítico que borrar

    # Solo preguntar si hay una foto registrada para borrar
    if path_to_delete and os.path.exists(path_to_delete):
         confirm = messagebox.askyesno("Confirmar Limpieza",
                                       f"¿Limpiar campos y borrar '{os.path.basename(path_to_delete)}' del disco?")

    if not confirm:
        actualizar_estado("Limpieza cancelada.", info=True)
        return

    text_area.delete('1.0', tk.END)
    text_area.insert('1.0', "Listo. Campos limpiados.")
    text_area.tag_remove(tk.ALL, "1.0", tk.END)
    text_area.tag_add("info", "1.0", tk.END)

    limpiar_imagen()

    deleted_msg = ""
    if path_to_delete:
        if os.path.exists(path_to_delete):
            try:
                os.remove(path_to_delete); print(f"Eliminado: {path_to_delete}")
                deleted_msg = f"\nArchivo '{os.path.basename(path_to_delete)}' eliminado."
                last_photo_path = None
            except Exception as e:
                print(f"Error al borrar {path_to_delete}: {e}")
                deleted_msg = f"\nError al borrar {os.path.basename(path_to_delete)}: {e}"
                # No reseteamos last_photo_path si falla
        else:
            # El path estaba guardado pero el archivo ya no existe
            deleted_msg = f"\nAdvertencia: {os.path.basename(path_to_delete)} ya no existía."
            last_photo_path = None # Reseteamos porque no existe
    # else: No había foto registrada

    # Habilitar botón Foto si todo está disponible
    take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)

    # Añadir mensaje de borrado si hubo alguno
    if deleted_msg:
         actualizar_estado(deleted_msg, append=True, info=("Error" not in deleted_msg and "Advertencia" not in deleted_msg), error=("Error" in deleted_msg))
    # Asegurar que el cursor se vea al final
    text_area.see(tk.END)


def limpiar_imagen():
    """Quita la imagen del label."""
    if not pillow_available: return
    image_label.configure(image=None, text="Imagen capturada aparecerá aquí", font=placeholder_font_style)
    image_label.image = None

def actualizar_estado(mensaje, error=False, success=False, info=False, append=False):
    """Actualiza el texto y color en el área de texto."""
    tags = {"error": COLOR_ERROR, "success": COLOR_SUCCESS, "info": COLOR_INFO}
    for tag_name, color in tags.items():
        if tag_name not in text_area.tag_names(): text_area.tag_configure(tag_name, foreground=color)

    tag_to_apply = None
    if error: tag_to_apply = "error"
    elif success: tag_to_apply = "success"
    elif info: tag_to_apply = "info"

    start_index = "1.0"
    if not append:
        text_area.delete("1.0", tk.END)
    else:
        # Asegurar newline antes de añadir si no existe
        if text_area.get("end-2c", "end-1c") != '\n': text_area.insert(tk.END, "\n")
        start_index = text_area.index(tk.END + "-1c")

    text_area.insert(tk.END, mensaje)
    end_index = text_area.index(tk.END + "-1c") # Antes del newline final automático de tk.Text

    if tag_to_apply:
         # Comprobar validez índices antes de aplicar tag
         if text_area.compare(start_index, ">=", "1.0") and text_area.compare(start_index, "<", end_index):
              text_area.tag_add(tag_to_apply, start_index, end_index)

    # Asegurar newline al final del widget
    if text_area.get("end-2c", "end-1c") != '\n': text_area.insert(tk.END, "\n")

    text_area.see(tk.END)


# --- Configuración de la Interfaz Gráfica (Mismos widgets y layout) ---

root = tk.Tk()
root.title("Captura y Clasificación (Perro/Gato)")
root.geometry("900x600")

# Paleta de Colores y Fuentes (sin cambios)
COLOR_PRIMARY = "#007bff"; COLOR_SECONDARY = "#6c757d"; COLOR_SUCCESS = "#28a745"
COLOR_ERROR = "#dc3545"; COLOR_INFO = "#17a2b8"; COLOR_BG = "#f8f9fa"
COLOR_FG = "#212529"; COLOR_BTN_FG = "#ffffff"; COLOR_PLACEHOLDER_BG = "#e9ecef"
root.configure(bg=COLOR_BG)
default_font_family = "Helvetica"; button_font_size = 13; text_area_font_size = 12; placeholder_font_size = 15
button_font_style = font.Font(family=default_font_family, size=button_font_size, weight='bold')
text_area_font_style = font.Font(family=default_font_family, size=text_area_font_size)
placeholder_font_style = font.Font(family=default_font_family, size=placeholder_font_size, slant='italic')

# Estilos ttk (sin cambios)
style = Style(root); style.theme_use('clam')
style.configure('TButton', font=button_font_style, padding=(12, 6))
style.map('TButton', foreground=[('disabled', '#adb5bd')], background=[('disabled', '#e9ecef')])
style.configure('Primary.TButton', background=COLOR_PRIMARY, foreground=COLOR_BTN_FG); style.map('Primary.TButton', background=[('active', '#0056b3'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])
style.configure('Secondary.TButton', background=COLOR_SECONDARY, foreground=COLOR_BTN_FG); style.map('Secondary.TButton', background=[('active', '#5a6268'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])
style.configure('TFrame', background=COLOR_BG)
style.configure('ImagePlaceholder.TLabel', background=COLOR_PLACEHOLDER_BG, foreground=COLOR_SECONDARY, font=placeholder_font_style, anchor=tk.CENTER, relief=tk.SOLID, borderwidth=1)

# Layout con Grid (sin cambios)
main_frame = ttk.Frame(root, padding="15 15 15 15", style='TFrame'); main_frame.pack(fill=tk.BOTH, expand=True)
main_frame.columnconfigure(0, weight=3); main_frame.columnconfigure(1, weight=1); main_frame.rowconfigure(0, weight=1)
image_label = ttk.Label(main_frame, text="Imagen capturada aparecerá aquí", style='ImagePlaceholder.TLabel'); image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
right_frame = ttk.Frame(main_frame, style='TFrame', padding=(10, 0)); right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
right_frame.rowconfigure(0, weight=3); right_frame.rowconfigure(1, weight=0); right_frame.rowconfigure(2, weight=0); right_frame.columnconfigure(0, weight=1); right_frame.columnconfigure(1, weight=0)
text_area = tk.Text(right_frame, height=10, width=30, wrap=tk.WORD, font=text_area_font_style, relief=tk.SOLID, borderwidth=1, fg=COLOR_FG, bg="white"); text_area.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=text_area.yview); scrollbar.grid(row=0, column=1, sticky='ns', pady=(0, 15)); text_area['yscrollcommand'] = scrollbar.set
take_photo_button = ttk.Button(right_frame, text="Foto", command=tomar_foto, style='Primary.TButton'); take_photo_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)
clear_button = ttk.Button(right_frame, text="Limpiar", command=limpiar_campos, style='Secondary.TButton'); clear_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

# --- Iniciar y Cargar Modelo ---
initial_message = "Listo."
error_message = ""
can_operate = True

if not picamera2_available: error_message += "Error: picamera2 no disponible.\n"; can_operate = False
if not pillow_available: error_message += "Error: Pillow no disponible.\n"; can_operate = False
if not tf_available: error_message += "Advertencia: TensorFlow no disponible. No se clasificará.\n"
# No deshabilitamos todo por TF, solo la clasificación

if error_message:
    actualizar_estado(error_message + ("Funcionalidad limitada." if can_operate else "Componentes críticos faltan."), error=not can_operate, info=can_operate and "Advertencia" in error_message)

# Intentar cargar el modelo después de crear la GUI (puede tardar)
if tf_available:
     # Ejecutar carga después de que la ventana principal esté lista
     root.after(100, cargar_modelo) # 100ms de espera
     if not error_message: # Si no hubo otros errores, poner mensaje inicial
         actualizar_estado(initial_message + "\nCargando modelo IA...", info=True)
elif not error_message: # No TF, pero otros componentes OK
     actualizar_estado(initial_message, info=True)


# Habilitar/deshabilitar botones basado en componentes críticos
if not can_operate:
    take_photo_button.config(state=tk.DISABLED)
    # clear_button.config(state=tk.DISABLED) # Limpiar puede seguir funcionando para texto
else:
     take_photo_button.config(state=tk.NORMAL) # Empezar habilitado si hw ok


root.mainloop()