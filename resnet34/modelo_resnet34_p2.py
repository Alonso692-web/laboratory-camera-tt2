import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import subprocess

# Configurar dispositivo
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Nombres de clases (ajusta estos nombres a los tuyos)
class_names = ['clase0', 'clase1', 'clase2', 'clase3', 'clase4', 'clase5', 'clase6', 'clase7', 'clase8']

# Capturar imagen con la cámara de la Raspberry Pi
image_path = "captura.jpg"
subprocess.run(["raspistill", "-o", image_path, "-w", "640", "-h", "480", "-t", "1000"], check=True)

# Cargar modelo SqueezeNet y ajustar la capa final a 9 clases
modelo = models.squeezenet1_1(weights=None)
modelo.classifier[1] = nn.Conv2d(512, 9, kernel_size=(1, 1), stride=(1, 1))
modelo.num_classes = 9
modelo.load_state_dict(torch.load("models/S15.pth", map_location=device))
modelo.to(device)
modelo.eval()

# Transformaciones para la imagen
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# Cargar y transformar la imagen
image_pil = Image.open(image_path).convert("RGB")
image_tensor = transform(image_pil).unsqueeze(0).to(device)

# Realizar la predicción
with torch.no_grad():
    output = modelo(image_tensor)
    _, predicted = torch.max(output, 1)
    predicted_class = predicted.item()

# Mostrar resultado
predicted_class_name = class_names[predicted_class]
print(f"✅ La clase predicha es: {predicted_class_name}")

# Mostrar la imagen original (no normalizada) con el visor por defecto del sistema
image_pil.show(title=f"Predicción: {predicted_class_name}")