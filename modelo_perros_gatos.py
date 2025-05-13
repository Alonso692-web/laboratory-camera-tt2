import tkinter as tk
from tkinter import font
import os
from datetime import datetime
from PIL import Image, ImageTk
import torch
from torchvision import models, transforms
import subprocess

# --- Modelo y Clasificación (sin cambios en su lógica interna) ---
model = models.resnet18(pretrained=True)
model.eval()

dog_indices = set(range(151, 269))
cat_indices = set([281, 282, 283, 284, 285])

def preprocess_image(image_path):
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    img = Image.open(image_path).convert('RGB')
    return preprocess(img).unsqueeze(0)

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
tk_image_ref = None

# --- Funciones de la Interfaz ---
def tomar_y_clasificar():
    global last_photo_path
    global tk_image_ref

    status_label.config(text="Capturando imagen...")
    root.update_idletasks()

    save_dir = "fotos"
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = f"captura_{timestamp}.jpg"
    ruta = os.path.join(save_dir, nombre)

    try:
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

    # Mostrar la imagen capturada en image_display_label
    try:
        img_pil = Image.open(ruta)
        img_pil.thumbnail((360, 260))
        tk_image_ref = ImageTk.PhotoImage(img_pil)
        image_display_label.config(image=tk_image_ref, text="") # Mostrar imagen
        root.update_idletasks()
    except Exception as e:
        status_label.config(text=f"Error al mostrar imagen: {e}")
        image_display_label.config(image=None, text="Error al mostrar")
        tk_image_ref = None
        # Aunque falle la muestra, intentamos clasificar
        
    # Clasificar
    resultado = classify_image(ruta)
    status_label.config(text=f"Resultado: {resultado}")

    # --- CORRECCIÓN AQUÍ ---
    # Ya NO borramos la imagen aquí. Se borrará al presionar "limpiar".
    # image_display_label.config(image=None, text="")
    # tk_image_ref = None

    last_photo_path = ruta

    foto_button.config(state=tk.DISABLED)
    limpiar_button.config(state=tk.NORMAL)

def limpiar_datos():
    global last_photo_path
    global tk_image_ref

    if last_photo_path and os.path.exists(last_photo_path):
        try:
            os.remove(last_photo_path)
        except OSError as e:
            print(f"No se pudo eliminar {last_photo_path}: {e}")
    last_photo_path = None

    # Restaurar el placeholder en el área de imagen
    image_display_label.config(image=None, text="imagen", fg="blue") # fg="blue" para que coincida con el estado inicial
    tk_image_ref = None # Liberar referencia a la imagen anterior

    status_label.config(text="Esperando acción...")

    foto_button.config(state=tk.NORMAL)
    limpiar_button.config(state=tk.DISABLED)


# --- Interfaz con Tkinter ---
root = tk.Tk()
root.title("Detector de Perro o Gato")
root.geometry("650x380")

main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

left_frame = tk.Frame(main_frame, width=400, height=300, bd=2, relief=tk.SOLID)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
left_frame.pack_propagate(False)

image_display_label = tk.Label(left_frame, text="imagen", fg="blue", font=font.Font(size=14))
image_display_label.pack(padx=20, pady=20, expand=True, fill=tk.BOTH)

right_frame = tk.Frame(main_frame, width=220, height=300, bd=2, relief=tk.SOLID)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
right_frame.pack_propagate(False)

status_label_container = tk.Frame(right_frame, height=150, bd=2, relief=tk.SOLID)
status_label_container.pack(pady=(10,5), padx=10, fill=tk.X)
status_label_container.pack_propagate(False)

status_label = tk.Label(
    status_label_container,
    text="Esperando acción...",
    font=font.Font(size=12),
    wraplength=180,
    justify=tk.LEFT,
    anchor="nw"
)
status_label.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)


buttons_container = tk.Frame(right_frame)
buttons_container.pack(pady=5, padx=10, fill=tk.X)

foto_button = tk.Button(buttons_container, text="foto", command=tomar_y_clasificar, width=18, height=2)
foto_button.pack(pady=(10,5))

limpiar_button = tk.Button(buttons_container, text="limpiar", command=limpiar_datos, width=18, height=2)
limpiar_button.pack(pady=5)
limpiar_button.config(state=tk.DISABLED)

root.mainloop()