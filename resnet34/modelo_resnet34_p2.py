import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import matplotlib.pyplot as plt
import subprocess

# Configurar dispositivo
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Nombres de clases (ajústalos a tus categorías)
class_names = ['clase0', 'clase1', 'clase2', 'clase3', 'clase4', 'clase5', 'clase6', 'clase7', 'clase8']

# Capturar imagen con la Raspberry Pi Camera
image_path = "captura.jpg"
subprocess.run(["raspistill", "-o", image_path, "-w", "640", "-h", "480", "-t", "1000"], check=True)

# Cargar modelo SqueezeNet con última capa adaptada
modelo = models.squeezenet1_1(weights=None)
modelo.classifier[1] = nn.Conv2d(512, 9, kernel_size=(1, 1), stride=(1, 1))  # 9 clases
modelo.num_classes = 9
modelo.load_state_dict(torch.load("models/S15.pth", map_location=device))
modelo.to(device)
modelo.eval()

# Definir transformaciones
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# Cargar imagen con PIL
image_pil = Image.open(image_path).convert("RGB")
image_tensor = transform(image_pil).unsqueeze(0).to(device)

# Predicción
with torch.no_grad():
    output = modelo(image_tensor)
    _, predicted = torch.max(output, 1)
    predicted_class = predicted.item()

predicted_class_name = class_names[predicted_class]
print(f"✅ La clase predicha es: {predicted_class_name}")

# Mostrar imagen original con predicción
plt.imshow(image_pil)
plt.axis('off')
plt.title(f"Predicción: {predicted_class_name}")
plt.show()