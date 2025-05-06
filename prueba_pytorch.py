import tkinter as tk
from tkinter import ttk, font, messagebox
from tkinter.ttk import Style
import time
from datetime import datetime
import os
import logging
import numpy as np # Sigue siendo necesario

# --- Pillow (PIL) ---
try:
    from PIL import Image, ImageTk
    pillow_available = True
except ImportError:
    print("Error: Pillow o ImageTk no encontrado.")
    pillow_available = False

# --- PyTorch y Torchvision ---
try:
    import torch
    import torchvision.transforms as T
    import torchvision.models as models
    pytorch_available = True
    print(f"PyTorch version: {torch.__version__}")
    print(f"Torchvision version: {torchvision.__version__}")
except ImportError:
    print("--------------------------------------------------")
    print("Error: PyTorch o Torchvision no encontrado.")
    print("La instalación en Raspberry Pi puede ser compleja.")
    print("Consulta: https://pytorch.org/get-started/locally/")
    print("O busca wheels precompilados para ARM.")
    print("La clasificación de imágenes estará deshabilitada.")
    print("--------------------------------------------------")
    pytorch_available = False
except Exception as e:
    print(f"Error al importar PyTorch/Torchvision: {e}")
    pytorch_available = False

# --- Picamera2 ---
try:
    from picamera2 import Picamera2
    picamera2_available = True
except ImportError: print("Error: picamera2 no disponible."); picamera2_available = False
except Exception as e: print(f"Error inicializando cámara: {e}"); picamera2_available = False

# --- Variables Globales ---
last_photo_path = None
pytorch_model = None # Para el modelo PyTorch cargado
pytorch_labels = None # Lista de etiquetas de ImageNet
pytorch_device = None # 'cpu' o 'cuda' (será 'cpu' en RPi)
pytorch_transforms = None # Transformaciones de preprocesamiento

# --- Constantes ---
LABELS_PATH = "imagenet_1000_labels.txt" # Mismo archivo de etiquetas

# --- Funciones ---

def cargar_modelo_pytorch():
    """Carga el modelo MobileNetV2 de PyTorch y las etiquetas."""
    global pytorch_model, pytorch_labels, pytorch_device, pytorch_transforms
    if not pytorch_available:
        print("PyTorch no disponible, no se carga modelo.")
        return False
    if pytorch_model is not None: # Ya cargado
        return True

    if not os.path.exists(LABELS_PATH):
        print(f"Error: Archivo de etiquetas no encontrado en {LABELS_PATH}")
        actualizar_estado(f"Error: Falta archivo {LABELS_PATH}", error=True, append=True)
        return False

    try:
        print("Configurando dispositivo PyTorch (CPU)...")
        pytorch_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Usando dispositivo: {pytorch_device}")

        print("Cargando modelo MobileNetV2 pre-entrenado de Torchvision...")
        pytorch_model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1) # O _V2
        pytorch_model.eval() # ¡MUY IMPORTANTE! Poner en modo evaluación
        pytorch_model.to(pytorch_device) # Mover modelo al dispositivo
        print("Modelo MobileNetV2 (PyTorch) cargado.")

        # Definir transformaciones de preprocesamiento
        # Estas son las transformaciones estándar para modelos ImageNet
        pytorch_transforms = T.Compose([
            T.Resize(256),             # Redimensionar lado más corto a 256
            T.CenterCrop(224),         # Cortar el centro a 224x224
            T.ToTensor(),              # Convertir a tensor PyTorch (escala a [0,1], C,H,W)
            T.Normalize(mean=[0.485, 0.456, 0.406], # Normalizar con medias y std de ImageNet
                          std=[0.229, 0.224, 0.225])
        ])
        print("Transformaciones de PyTorch definidas.")

        # Cargar etiquetas
        print(f"Cargando etiquetas desde {LABELS_PATH}...")
        with open(LABELS_PATH, 'r') as f:
            pytorch_labels = [line.strip().split(' ', 1)[1] if ' ' in line else line.strip() for line in f.readlines()]
        # El modelo MobileNetV2 de torchvision produce 1000 clases directamente
        # así que no es necesario quitar 'background' como en algunos TFLite.
        print(f"{len(pytorch_labels)} etiquetas cargadas.")
        return True

    except Exception as e:
        print(f"Error crítico al cargar modelo/etiquetas PyTorch: {e}")
        actualizar_estado(f"Error cargando IA (PyTorch): {e}", error=True, append=True)
        pytorch_model = None; pytorch_labels = None
        return False

def preprocesar_imagen_pytorch(img_path):
    """Carga y preprocesa la imagen para el modelo PyTorch."""
    if not pillow_available or pytorch_transforms is None or pytorch_device is None:
        return None
    try:
        img = Image.open(img_path).convert('RGB')
        # Aplicar transformaciones
        input_tensor = pytorch_transforms(img)
        # Añadir dimensión de batch (B,C,H,W)
        input_batch = input_tensor.unsqueeze(0)
        # Mover al dispositivo
        return input_batch.to(pytorch_device)
    except Exception as e:
        print(f"Error al preprocesar imagen para PyTorch: {e}")
        return None

def clasificar_imagen_pytorch(img_path):
    """Clasifica la imagen usando PyTorch y busca perros/gatos."""
    if pytorch_model is None or pytorch_labels is None or pytorch_device is None:
        return "Componentes IA (PyTorch) no cargados."

    input_tensor = preprocesar_imagen_pytorch(img_path)
    if input_tensor is None:
        return "Error al preprocesar imagen para IA (PyTorch)."

    try:
        with torch.no_grad(): # ¡IMPORTANTE para inferencia!
            output = pytorch_model(input_tensor)

        # Aplicar Softmax para obtener probabilidades
        probabilities = torch.nn.functional.softmax(output[0], dim=0)

        # Obtener top 3 predicciones
        top3_prob, top3_catid = torch.topk(probabilities, 3)

        results = []
        for i in range(top3_prob.size(0)):
            cat_id = top3_catid[i].item()
            prob = top3_prob[i].item()
            if 0 <= cat_id < len(pytorch_labels):
                 results.append({'label': pytorch_labels[cat_id], 'score': prob})
            else:
                 print(f"ID de categoría fuera de rango: {cat_id}")


        print("Predicciones PyTorch:", results)

        # Buscar 'cat' o 'dog'
        resultado_final = "No se detectó Perro/Gato"
        detected = False
        for res in results:
            label_lower = res['label'].lower()
            prob = res['score']
            if 'cat' in label_lower:
                 resultado_final = f"Detectado: Gato ({res['label']}, {prob:.2%})"
                 detected = True; break
            elif 'dog' in label_lower:
                 resultado_final = f"Detectado: Perro ({res['label']}, {prob:.2%})"
                 detected = True; break

        if not detected and results:
             top_pred_label = results[0]['label']
             top_pred_prob = results[0]['score']
             resultado_final = f"Detectado: {top_pred_label} ({top_pred_prob:.2%})"
        elif not results:
             resultado_final = "No se obtuvieron resultados válidos de IA (PyTorch)."

        return resultado_final

    except Exception as e:
        print(f"Error durante la clasificación PyTorch: {e}")
        return "Error durante la clasificación IA (PyTorch)."


def tomar_foto():
    """Captura, guarda, muestra, CLASIFICA (PyTorch) y deshabilita botón."""
    global last_photo_path
    if not picamera2_available: actualizar_estado("Error: picamera2 no disponible.", error=True); return
    if not pillow_available: actualizar_estado("Error: Pillow no disponible.", error=True); return

    if not pytorch_model and pytorch_available: # Modelo no cargado pero PyTorch sí
         if not cargar_modelo_pytorch():
              actualizar_estado("Fallo al cargar modelo PyTorch. No se puede clasificar.", error=True)

    clear_button.config(state=tk.DISABLED); take_photo_button.config(state=tk.DISABLED)
    actualizar_estado("Iniciando cámara...", info=True); root.update_idletasks()
    picam2 = None; success = False; clasificacion_result = "(Clasificación PyTorch no disp.)"

    try:
        picam2 = Picamera2(); save_dir = "fotos_capturadas"; os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S"); nombre_archivo = f"foto_{timestamp}.jpg"
        ruta_completa = os.path.join(save_dir, nombre_archivo)

        config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="lores")
        picam2.configure(config); picam2.start()

        actualizar_estado("Ajustando...", info=True); root.update_idletasks(); time.sleep(1.5)
        actualizar_estado(f"Capturando: {nombre_archivo}...", info=True); root.update_idletasks()

        metadata = picam2.capture_file(ruta_completa); print("Metadatos:", metadata)
        last_photo_path = ruta_completa; mostrar_imagen(ruta_completa)

        actualizar_estado(f"Foto guardada.\nClasificando con PyTorch...", info=True)
        root.update_idletasks()

        if pytorch_available and pytorch_model:
             start_time = time.monotonic()
             clasificacion_result = clasificar_imagen_pytorch(ruta_completa)
             end_time = time.monotonic()
             print(f"Resultado PyTorch: {clasificacion_result}")
             print(f"Tiempo de Inferencia PyTorch: {end_time - start_time:.3f} segundos")
             clasificacion_result += f" ({(end_time - start_time):.2f}s)"
        elif not pytorch_available:
             clasificacion_result = "(PyTorch no instalado)"
        else:
             clasificacion_result = "(Modelo PyTorch no cargado)"

        actualizar_estado(f"Previsualización mostrada.\n{clasificacion_result}", success=True)
        success = True

    except Exception as e:
        mensaje_error = f"Error en toma/clasif. PyTorch: {e}"; print(mensaje_error)
        actualizar_estado(mensaje_error, error=True); limpiar_imagen()
        take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)

    finally:
        if picam2 and picam2.started: picam2.stop(); picam2.close(); print("Cámara detenida.")
        clear_button.config(state=tk.NORMAL)
        # El botón Foto queda deshabilitado si success=True


# --- Funciones mostrar_imagen, limpiar_campos, limpiar_imagen, actualizar_estado (sin cambios lógicos) ---
# ... (Las funciones de la GUI y manipulación de archivos son las mismas que en la versión TFLite) ...
# (Por brevedad, no las repito aquí, asume que son las mismas que en la respuesta anterior)
def mostrar_imagen(ruta_imagen):
    if not pillow_available: return
    try:
        img = Image.open(ruta_imagen); img_width, img_height = img.size
        image_label.update_idletasks(); label_width = image_label.winfo_width(); label_height = image_label.winfo_height()
        if label_width <= 1 or label_height <= 1: label_width, label_height = 600, 450
        img_aspect = img_width / float(img_height); label_aspect = label_width / float(label_height)
        target_width = label_width - 10; target_height = label_height - 10
        if img_aspect > label_aspect: new_width = int(target_width); new_height = int(new_width / img_aspect)
        else: new_height = int(target_height); new_width = int(new_height * img_aspect)
        if new_width <= 0 : new_width = 1; if new_height <= 0 : new_height = 1
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized_img)
        image_label.configure(image=photo, text=""); image_label.image = photo
    except FileNotFoundError: print(f"Error: No se encontró: {ruta_imagen}"); actualizar_estado(f"Error: Archivo no encontrado {os.path.basename(ruta_imagen)}", error=True, append=True); limpiar_imagen()
    except Exception as e: print(f"Error al mostrar imagen: {e}"); actualizar_estado(f"Error al mostrar imagen: {e}", error=True, append=True); limpiar_imagen()

def limpiar_campos():
    global last_photo_path; path_to_delete = last_photo_path; confirm = True
    if path_to_delete and os.path.exists(path_to_delete): confirm = messagebox.askyesno("Confirmar Limpieza", f"¿Limpiar campos y borrar '{os.path.basename(path_to_delete)}' del disco?")
    if not confirm: actualizar_estado("Limpieza cancelada.", info=True); return
    text_area.delete('1.0', tk.END); text_area.insert('1.0', "Listo. Campos limpiados."); text_area.tag_remove(tk.ALL, "1.0", tk.END); text_area.tag_add("info", "1.0", tk.END)
    limpiar_imagen(); deleted_msg = ""
    if path_to_delete:
        if os.path.exists(path_to_delete):
            try: os.remove(path_to_delete); print(f"Eliminado: {path_to_delete}"); deleted_msg = f"\nArchivo '{os.path.basename(path_to_delete)}' eliminado."; last_photo_path = None
            except Exception as e: print(f"Error al borrar {path_to_delete}: {e}"); deleted_msg = f"\nError al borrar {os.path.basename(path_to_delete)}: {e}"
        else: deleted_msg = f"\nAdvertencia: {os.path.basename(path_to_delete)} ya no existía."; last_photo_path = None
    take_photo_button.config(state=tk.NORMAL if picamera2_available and pillow_available else tk.DISABLED)
    if deleted_msg: actualizar_estado(deleted_msg, append=True, info=("Error" not in deleted_msg and "Advertencia" not in deleted_msg), error=("Error" in deleted_msg))
    text_area.see(tk.END)

def limpiar_imagen():
    if not pillow_available: return
    image_label.configure(image=None, text="Imagen capturada aparecerá aquí", font=placeholder_font_style); image_label.image = None

def actualizar_estado(mensaje, error=False, success=False, info=False, append=False):
    tags = {"error": COLOR_ERROR, "success": COLOR_SUCCESS, "info": COLOR_INFO}
    for tag_name, color in tags.items():
        if tag_name not in text_area.tag_names(): text_area.tag_configure(tag_name, foreground=color)
    tag_to_apply = None
    if error: tag_to_apply = "error"; elif success: tag_to_apply = "success"; elif info: tag_to_apply = "info"
    start_index = "1.0"
    if not append: text_area.delete("1.0", tk.END)
    else:
        if text_area.get("end-2c", "end-1c") != '\n': text_area.insert(tk.END, "\n")
        start_index = text_area.index(tk.END + "-1c")
    text_area.insert(tk.END, mensaje); end_index = text_area.index(tk.END + "-1c")
    if tag_to_apply:
         if text_area.compare(start_index, ">=", "1.0") and text_area.compare(start_index, "<", end_index): text_area.tag_add(tag_to_apply, start_index, end_index)
    if text_area.get("end-2c", "end-1c") != '\n': text_area.insert(tk.END, "\n")
    text_area.see(tk.END)

# --- Configuración de la Interfaz Gráfica (Sin cambios en widgets/layout) ---
root = tk.Tk(); root.title("Captura y Clasificación PyTorch (Perro/Gato)"); root.geometry("900x600")
COLOR_PRIMARY = "#007bff"; COLOR_SECONDARY = "#6c757d"; COLOR_SUCCESS = "#28a745"; COLOR_ERROR = "#dc3545"; COLOR_INFO = "#17a2b8"; COLOR_BG = "#f8f9fa"; COLOR_FG = "#212529"; COLOR_BTN_FG = "#ffffff"; COLOR_PLACEHOLDER_BG = "#e9ecef"
root.configure(bg=COLOR_BG); default_font_family = "Helvetica"; button_font_size = 13; text_area_font_size = 12; placeholder_font_size = 15
button_font_style = font.Font(family=default_font_family, size=button_font_size, weight='bold'); text_area_font_style = font.Font(family=default_font_family, size=text_area_font_size); placeholder_font_style = font.Font(family=default_font_family, size=placeholder_font_size, slant='italic')
style = Style(root); style.theme_use('clam'); style.configure('TButton', font=button_font_style, padding=(12, 6)); style.map('TButton', foreground=[('disabled', '#adb5bd')], background=[('disabled', '#e9ecef')])
style.configure('Primary.TButton', background=COLOR_PRIMARY, foreground=COLOR_BTN_FG); style.map('Primary.TButton', background=[('active', '#0056b3'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])
style.configure('Secondary.TButton', background=COLOR_SECONDARY, foreground=COLOR_BTN_FG); style.map('Secondary.TButton', background=[('active', '#5a6268'), ('disabled', '#e9ecef')], foreground=[('disabled', '#adb5bd')])
style.configure('TFrame', background=COLOR_BG); style.configure('ImagePlaceholder.TLabel', background=COLOR_PLACEHOLDER_BG, foreground=COLOR_SECONDARY, font=placeholder_font_style, anchor=tk.CENTER, relief=tk.SOLID, borderwidth=1)
main_frame = ttk.Frame(root, padding="15 15 15 15", style='TFrame'); main_frame.pack(fill=tk.BOTH, expand=True); main_frame.columnconfigure(0, weight=3); main_frame.columnconfigure(1, weight=1); main_frame.rowconfigure(0, weight=1)
image_label = ttk.Label(main_frame, text="Imagen capturada aparecerá aquí", style='ImagePlaceholder.TLabel'); image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
right_frame = ttk.Frame(main_frame, style='TFrame', padding=(10, 0)); right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0); right_frame.rowconfigure(0, weight=3); right_frame.rowconfigure(1, weight=0); right_frame.rowconfigure(2, weight=0); right_frame.columnconfigure(0, weight=1); right_frame.columnconfigure(1, weight=0)
text_area = tk.Text(right_frame, height=10, width=30, wrap=tk.WORD, font=text_area_font_style, relief=tk.SOLID, borderwidth=1, fg=COLOR_FG, bg="white"); text_area.grid(row=0, column=0, sticky="nsew", pady=(0, 15)); scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=text_area.yview); scrollbar.grid(row=0, column=1, sticky='ns', pady=(0, 15)); text_area['yscrollcommand'] = scrollbar.set
take_photo_button = ttk.Button(right_frame, text="Foto", command=tomar_foto, style='Primary.TButton'); take_photo_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)
clear_button = ttk.Button(right_frame, text="Limpiar", command=limpiar_campos, style='Secondary.TButton'); clear_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

# --- Iniciar y Cargar Modelo PyTorch ---
initial_message = "Listo."
error_message = ""
can_operate = True
if not picamera2_available: error_message += "Error: picamera2 no disponible.\n"; can_operate = False
if not pillow_available: error_message += "Error: Pillow no disponible.\n"; can_operate = False
if not pytorch_available: error_message += "Advertencia: PyTorch no disponible. No se clasificará.\n"

if error_message: actualizar_estado(error_message + ("Funcionalidad limitada." if can_operate else "Componentes críticos faltan."), error=not can_operate, info=can_operate and "Advertencia" in error_message)

if pytorch_available:
     root.after(200, cargar_modelo_pytorch) # Dar un poco más de tiempo para la GUI
     if not error_message: actualizar_estado(initial_message + "\nCargando modelo PyTorch...", info=True)
elif not error_message:
     actualizar_estado(initial_message, info=True)

if not can_operate: take_photo_button.config(state=tk.DISABLED)
else: take_photo_button.config(state=tk.NORMAL)

root.mainloop()