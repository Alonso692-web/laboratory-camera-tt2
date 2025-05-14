import os
import subprocess
from PIL import Image
import torch
import torch.nn as nn
from torchvision import models, transforms

# 1. Configurar dispositivo
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 2. Clases según tu modelo (ajusta el orden)
class_names = ['clase0', 'clase1', 'clase2', 'clase3', 'clase4', 'clase5', 'clase6', 'clase7', 'clase8']

# 3. Capturar imagen con la cámara de la Raspberry Pi
image_path = "captura.jpg"
print("Capturando imagen...")
subprocess.run(["raspistill", "-o", image_path, "-w", "640", "-h", "480", "-t", "1000"], check=True)

# 4. Preprocesamiento de la imagen
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# 5. Cargar modelo ResNet34 con pesos entrenados
model = models.resnet34(pretrained=False)
model.fc = nn.Linear(model.fc.in_features, 9)
model.load_state_dict(torch.load("R23.pth", map_location=device))
model.to(device)
model.eval()

# 6. Cargar imagen y predecir
image = Image.open(image_path).convert("RGB")
input_tensor = transform(image).unsqueeze(0).to(device)

with torch.no_grad():
    outputs = model(input_tensor)
    _, predicted = torch.max(outputs, 1)
    pred_class = class_names[predicted.item()]

print(f"✅ Predicción: {pred_class}")
