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
# Aumentar base font size para máxima visibilidad
BASE_FONT_SIZE = 18  # Letras mucho más grandes

# --- Funciones de la Interfaz ---
def tomar_y_clasificar():
    global last_photo_path, tk_image_ref

    status_label.config(text="Capturando...")
    root.update_idletasks()

    save_dir = "fotos"
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = f"captura_{timestamp}.jpg"
    ruta = os.path.join(save_dir, nombre)

    try:
        subprocess.run(["libcamera-jpeg", "-n", "-o", ruta, "-t", "200"], check=True)
        status_label.config(text="Clasificando...")
        root.update_idletasks()
    except subprocess.CalledProcessError as e:
        status_label.config(text=f"Error captura: {e}")
        foto_button.config(state=tk.NORMAL)
        limpiar_button.config(state=tk.DISABLED)
        return
    except FileNotFoundError:
        status_label.config(text="Error: libcamera-jpeg no encontrado.")
        foto_button.config(state=tk.NORMAL)
        limpiar_button.config(state=tk.DISABLED)
        return

    # Mostrar imagen capturada con tamaño fijo de miniatura
    try:
        img_pil = Image.open(ruta)
        max_w, max_h = 180, 140  # Tamaño fijo de miniatura
        img_pil.thumbnail((max_w, max_h), Image.LANCZOS)
        tk_image_ref = ImageTk.PhotoImage(img_pil)
        image_display_label.config(image=tk_image_ref, text="")
        root.update_idletasks()
    except Exception as e:
        status_label.config(text=f"Error al mostrar: {e}")
        image_display_label.config(image=None, text="Error img")
        tk_image_ref = None

    resultado = classify_image(ruta)
    status_label.config(text=f"Es: {resultado}")

    last_photo_path = ruta

    foto_button.config(state=tk.DISABLED)
    limpiar_button.config(state=tk.NORMAL)


def limpiar_datos():
    global last_photo_path, tk_image_ref

    if last_photo_path and os.path.exists(last_photo_path):
        try:
            os.remove(last_photo_path)
        except OSError:
            pass
    last_photo_path = None

    image_display_label.config(image=None, text="imagen", fg="blue")
    tk_image_ref = None

    status_label.config(text="Esperando...")

    foto_button.config(state=tk.NORMAL)
    limpiar_button.config(state=tk.DISABLED)

# --- Interfaz con Tkinter ---
root = tk.Tk()
root.title("Detector")
# Dimensiones target para pantalla pequeña (3.5")
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")

# Configuración de rejilla raíz
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

main_frame = tk.Frame(root, padx=2, pady=2)
main_frame.grid(row=0, column=0, sticky="nsew")
main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_columnconfigure(0, weight=3)
main_frame.grid_columnconfigure(1, weight=2)

left_frame = tk.Frame(main_frame, bd=1, relief=tk.SOLID)
left_frame.grid(row=0, column=0, sticky="nsew", padx=(0,2))
left_frame.grid_rowconfigure(0, weight=1)
left_frame.grid_columnconfigure(0, weight=1)

image_display_label = tk.Label(
    left_frame,
    text="imagen",
    fg="blue",
    font=font.Font(size=BASE_FONT_SIZE + 2)
)
image_display_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

right_frame = tk.Frame(main_frame, bd=1, relief=tk.SOLID)
right_frame.grid(row=0, column=1, sticky="nsew", padx=(2,0))
right_frame.grid_rowconfigure(0, weight=1)
right_frame.grid_rowconfigure(1, weight=0)
right_frame.grid_columnconfigure(0, weight=1)

status_label_container = tk.Frame(right_frame, bd=1, relief=tk.SOLID)
status_label_container.grid(row=0, column=0, sticky="nsew", pady=(2,2), padx=2)
status_label_container.grid_rowconfigure(0, weight=1)
status_label_container.grid_columnconfigure(0, weight=1)

status_label = tk.Label(
    status_label_container,
    text="Esperando...",
    font=font.Font(size=BASE_FONT_SIZE),
    wraplength=(SCREEN_WIDTH * 2 // 5) - 20,
    justify=tk.LEFT,
    anchor="nw"
)
status_label.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

buttons_container = tk.Frame(right_frame)
buttons_container.grid(row=1, column=0, sticky="ew", pady=2, padx=2)
buttons_container.grid_columnconfigure(0, weight=1)

foto_button = tk.Button(
    buttons_container,
    text="foto",
    command=tomar_y_clasificar,
    font=font.Font(size=BASE_FONT_SIZE)
)
foto_button.grid(row=0, column=0, sticky="ew", pady=(2,1))

limpiar_button = tk.Button(
    buttons_container,
    text="limpiar",
    command=limpiar_datos,
    font=font.Font(size=BASE_FONT_SIZE)
)
limpiar_button.grid(row=1, column=0, sticky="ew", pady=(1,2))
limpiar_button.config(state=tk.DISABLED)

root.update_idletasks()
root.mainloop()