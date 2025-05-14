import tkinter as tk
from tkinter import font
import os
from datetime import datetime
from PIL import Image, ImageTk
import torch
import torch.nn as nn
from torchvision import models, transforms
import subprocess

# Configurar dispositivo
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Definir nombres de clases (9 clases)
class_names = ['clase0', 'clase1', 'clase2', 'clase3', 'clase4', 'clase5', 'clase6', 'clase7', 'clase8']

# Cargar modelo ResNet34 y ajustar capa final\ nmodel = models.resnet34(pretrained=False)
model.fc = nn.Linear(model.fc.in_features, len(class_names))
model.load_state_dict(torch.load('R23.pth', map_location=device))
model.to(device)
model.eval()

# Transformaciones para la imagen
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# Variables globales
last_photo_path = None

# Función de clasificación usando el modelo de 9 clases
def classify_image(image_path):
    image = Image.open(image_path).convert('RGB')
    tensor = transform(image).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
        _, pred = torch.max(outputs, 1)
        idx = pred.item()
    return class_names[idx]

# Función para capturar imagen y clasificar
def tomar_y_clasificar():
    global last_photo_path
    status_label.config(text='Capturando imagen...')
    root.update_idletasks()

    save_dir = 'fotos'
    os.makedirs(save_dir, exist_ok=True)
    nombre = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta = os.path.join(save_dir, nombre)

    # Captura con libcamera-jpeg usando subprocess
    try:
        subprocess.run(['libcamera-jpeg', '-o', ruta, '-t', '2000'], check=True)
    except subprocess.CalledProcessError as e:
        status_label.config(text=f"Error al capturar: {e}")
        return

    # Mostrar imagen más grande
    try:
        img = Image.open(ruta)
        img = img.resize((500, 400))
        tk_img = ImageTk.PhotoImage(img)
        img_label.config(image=tk_img)
        img_label.image = tk_img
        last_photo_path = ruta
    except Exception as e:
        status_label.config(text=f"Error al mostrar imagen: {e}")
        return

    # Clasificar y mostrar resultado
    resultado = classify_image(ruta)
    status_label.config(text=f"Predicción: {resultado}")
    boton.config(state=tk.DISABLED)
    limpiar_boton.config(state=tk.NORMAL)

# Función para limpiar interfaz
def limpiar():
    global last_photo_path
    img_label.config(image='')
    img_label.image = None
    status_label.config(text='Esperando acción...')
    boton.config(state=tk.NORMAL)
    limpiar_boton.config(state=tk.DISABLED)

    if last_photo_path and os.path.exists(last_photo_path):
        os.remove(last_photo_path)
        last_photo_path = None

# --- Interfaz con Tkinter ---
root = tk.Tk()
root.title('Clasificador de 9 Clases')
root.geometry('600x650')

fuente_titulo = font.Font(size=20, weight='bold')
fuente_estado = font.Font(size=14)

titulo = tk.Label(root, text='Clasificación de 9 Clases', font=fuente_titulo)
titulo.pack(pady=10)

img_label = tk.Label(root)
img_label.pack(pady=10)

boton = tk.Button(root, text='Tomar Foto', command=tomar_y_clasificar, width=20, height=2, font=font.Font(size=12))
boton.pack(pady=10)

limpiar_boton = tk.Button(root, text='Limpiar', command=limpiar, width=20, height=2, font=font.Font(size=12), state=tk.DISABLED)
limpiar_boton.pack(pady=5)

status_label = tk.Label(root, text='Esperando acción...', font=fuente_estado)
status_label.pack(pady=10)

root.mainloop()