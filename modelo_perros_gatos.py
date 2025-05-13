import tkinter as tk
from tkinter import font
import os
from datetime import datetime
from PIL import Image, ImageTk
import torch
from torchvision import models, transforms
import subprocess

# --- Modelo y Clasificación (sin cambios en su lógica interna) ---
# Modelo preentrenado
model = models.resnet18(pretrained=True)
model.eval()

# Índices de ImageNet
dog_indices = set(range(151, 269))    # Perros
cat_indices = set([281, 282, 283, 284, 285])  # Gatos

# Preprocesamiento
def preprocess_image(image_path):
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    img = Image.open(image_path).convert('RGB') # Asegurar que la imagen sea RGB
    return preprocess(img).unsqueeze(0)

# Clasificación
def classify_image(image_path):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    input_tensor = preprocess_image(image_path).to(device)
    model.to(device)
    with torch.no_grad():
        outputs = model(input_tensor)
        _, predicted = torch.max(outputs, 1)
        idx = predicted.item()
    if idx in dog_indices:
        return "Perro"
    elif idx in cat_indices:
        return "Gato"
    else:
        return "Ni perro ni gato"

# --- Variables Globales ---
last_photo_path = None
# Para mantener la referencia a la imagen de Tkinter y evitar que sea eliminada por el recolector de basura
tk_image_ref = None 

# --- Funciones de la Interfaz ---
def tomar_y_clasificar():
    global last_photo_path
    global tk_image_ref # Necesitamos modificar esta referencia global

    status_label.config(text="Capturando imagen...")
    root.update_idletasks()

    save_dir = "fotos"
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = f"captura_{timestamp}.jpg"
    ruta = os.path.join(save_dir, nombre)

    try:
        # Usamos -n (o --nopreview) para que libcamera-jpeg no muestre su propia ventana de preview
        # -t 500 es 0.5 segundos para la captura. Ajustar si es necesario.
        subprocess.run(["libcamera-jpeg", "-n", "-o", ruta, "-t", "500"], check=True)
        status_label.config(text="Imagen capturada. Clasificando...")
        root.update_idletasks()
    except subprocess.CalledProcessError as e:
        status_label.config(text=f"Error al capturar: {e}")
        foto_button.config(state=tk.NORMAL) 
        limpiar_button.config(state=tk.DISABLED)
        return
    except FileNotFoundError:
        status_label.config(text="Error: libcamera-jpeg no encontrado.")
        foto_button.config(state=tk.NORMAL)
        limpiar_button.config(state=tk.DISABLED)
        return

    # Mostrar la imagen capturada temporalmente en image_display_label
    try:
        img_pil = Image.open(ruta)
        # Ajustar tamaño al contenedor. left_frame (400x300), image_display_label con padding 20px.
        # Espacio disponible para la imagen: 360x260.
        img_pil.thumbnail((360, 260)) 
        tk_image_ref = ImageTk.PhotoImage(img_pil)
        image_display_label.config(image=tk_image_ref, text="") # Mostrar imagen, borrar texto placeholder
        root.update_idletasks() 
    except Exception as e:
        status_label.config(text=f"Error al mostrar imagen: {e}")
        image_display_label.config(image=None, text="") # Limpiar por si acaso
        tk_image_ref = None
        # Continuar con la clasificación de todas formas

    # Clasificar
    resultado = classify_image(ruta)
    status_label.config(text=f"Resultado: {resultado}")

    # "elimine el preview al tomar la foto": Limpiar la imagen del image_display_label
    image_display_label.config(image=None, text="") # Dejar en blanco hasta limpiar
    tk_image_ref = None # Borrar referencia

    last_photo_path = ruta  # Guardar ruta para borrarla con "limpiar"

    # Deshabilitar botón de tomar foto, habilitar botón de limpiar
    foto_button.config(state=tk.DISABLED)
    limpiar_button.config(state=tk.NORMAL)

def limpiar_datos():
    global last_photo_path
    global tk_image_ref

    # Borrar el archivo de la foto anterior
    if last_photo_path and os.path.exists(last_photo_path):
        try:
            os.remove(last_photo_path)
        except OSError as e:
            # Podríamos mostrar un error temporal en status_label si falla la eliminación
            print(f"No se pudo eliminar {last_photo_path}: {e}") # Log a consola
    last_photo_path = None

    # Restaurar el placeholder en el área de imagen
    image_display_label.config(image=None, text="imagen", fg="blue")
    tk_image_ref = None

    # Resetear el label de estado
    status_label.config(text="Esperando acción...")

    # Habilitar botón de tomar foto, deshabilitar botón de limpiar
    foto_button.config(state=tk.NORMAL)
    limpiar_button.config(state=tk.DISABLED)


# --- Interfaz con Tkinter ---
root = tk.Tk()
root.title("Detector de Perro o Gato")
root.geometry("650x380") # Geometría ajustada para el nuevo layout

# Frame principal que contendrá las secciones izquierda y derecha
main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Frame izquierdo para el display de la imagen ("imagen")
left_frame = tk.Frame(main_frame, width=400, height=300, bd=2, relief=tk.SOLID)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
left_frame.pack_propagate(False) # Evitar que el frame cambie de tamaño con su contenido

image_display_label = tk.Label(left_frame, text="imagen", fg="blue", font=font.Font(size=14))
image_display_label.pack(padx=20, pady=20, expand=True, fill=tk.BOTH)

# Frame derecho para los controles
right_frame = tk.Frame(main_frame, width=220, height=300, bd=2, relief=tk.SOLID) # Ancho ajustado
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
right_frame.pack_propagate(False)

# Frame para el "campo de texto" (status_label) para controlar su tamaño y borde
status_label_container = tk.Frame(right_frame, height=150, bd=2, relief=tk.SOLID)
status_label_container.pack(pady=(10,5), padx=10, fill=tk.X)
status_label_container.pack_propagate(False)

status_label = tk.Label(
    status_label_container, 
    text="Esperando acción...", 
    font=font.Font(size=12),
    wraplength=180, # Ajustar wraplength al ancho del contenedor menos padding
    justify=tk.LEFT, 
    anchor="nw" # Alinear texto arriba a la izquierda
)
status_label.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

# Frame para los botones para agruparlos
buttons_container = tk.Frame(right_frame)
buttons_container.pack(pady=5, padx=10, fill=tk.X) # fill=tk.X para que los botones puedan centrarse si es necesario

foto_button = tk.Button(buttons_container, text="foto", command=tomar_y_clasificar, width=18, height=2)
foto_button.pack(pady=(10,5)) 

limpiar_button = tk.Button(buttons_container, text="limpiar", command=limpiar_datos, width=18, height=2)
limpiar_button.pack(pady=5)
limpiar_button.config(state=tk.DISABLED) # Inicialmente deshabilitado

root.mainloop()