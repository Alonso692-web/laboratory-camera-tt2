import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image, ImageDraw, ImageFont
import subprocess

# Configurar dispositivo
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Lista de nombres de clases (ajústala a tu caso)
class_names = ['clase0', 'clase1', 'clase2', 'clase3', 'clase4', 'clase5', 'clase6', 'clase7', 'clase8']

# Ruta de la imagen capturada
image_path = "captura.jpg"

# Capturar imagen con la cámara de Raspberry Pi
subprocess.run(["raspistill", "-o", image_path, "-w", "640", "-h", "480", "-t", "1000"], check=True)

# Cargar modelo ResNet34 y modificar la última capa
modelo = models.resnet34(pretrained=False)
modelo.fc = nn.Linear(modelo.fc.in_features, 9)  # 9 clases
modelo.load_state_dict(torch.load("R23.pth", map_location=device))
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

# Cargar imagen original y convertir a RGB
image_pil = Image.open(image_path).convert("RGB")
image_tensor = transform(image_pil).unsqueeze(0).to(device)

# Realizar predicción
with torch.no_grad():
    output = modelo(image_tensor)
    _, predicted = torch.max(output, 1)
    predicted_class = predicted.item()

predicted_class_name = class_names[predicted_class]
print(f"✅ La clase predicha es: {predicted_class_name}")

# Dibujar la clase predicha en la imagen
draw = ImageDraw.Draw(image_pil)
try:
    # Usar fuente del sistema (opcional)
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
except:
    font = ImageFont.load_default()

draw.text((10, 10), f"Predicción: {predicted_class_name}", fill="red", font=font)

# Mostrar la imagen
image_pil.show()