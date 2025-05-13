import tkinter as tk
from tkinter import font
import os
from datetime import datetime
from PIL import Image, ImageTk
import torch
from torchvision import models, transforms
import subprocess  # Usaremos libcamera-jpeg desde bash

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
    img = Image.open(image_path).convert('RGB')
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

# Función para capturar imagen y clasificar
def tomar_y_clasificar():
    status_label.config(text="Capturando imagen...")
    root.update_idletasks()

    save_dir = "fotos"
    os.makedirs(save_dir, exist_ok=True)
    nombre = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta = os.path.join(save_dir, nombre)

    # Captura con libcamera-jpeg usando subprocess
    try:
        subprocess.run(["libcamera-jpeg", "-o", ruta, "-t", "2000"], check=True)
    except subprocess.CalledProcessError as e:
        status_label.config(text=f"Error al capturar: {e}")
        return

    # Mostrar imagen
    try:
        img = Image.open(ruta)
        img.thumbnail((300, 300))
        tk_img = ImageTk.PhotoImage(img)
        img_label.config(image=tk_img)
        img_label.image = tk_img
    except Exception as e:
        status_label.config(text=f"Error al mostrar imagen: {e}")
        return

    # Clasificar
    resultado = classify_image(ruta)
    status_label.config(text=f"Resultado: {resultado}")

# --- Interfaz con Tkinter ---
root = tk.Tk()
root.title("Detector de Perro o Gato")
root.geometry("400x500")

titulo = tk.Label(root, text="¿Es Perro o Gato?", font=font.Font(size=16, weight='bold'))
titulo.pack(pady=10)

img_label = tk.Label(root)
img_label.pack(pady=10)

boton = tk.Button(root, text="Tomar Foto", command=tomar_y_clasificar, width=20, height=2)
boton.pack(pady=20)

status_label = tk.Label(root, text="Esperando acción...", font=font.Font(size=12))
status_label.pack(pady=10)

root.mainloop()
