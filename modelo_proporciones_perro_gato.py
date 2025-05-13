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
# Define a smaller base font size
BASE_FONT_SIZE = 8 # Adjust as needed for your 3.5" screen

# --- Funciones de la Interfaz ---
def tomar_y_clasificar():
    global last_photo_path
    global tk_image_ref

    status_label.config(text="Capturando...")
    root.update_idletasks()

    save_dir = "fotos"
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = f"captura_{timestamp}.jpg"
    ruta = os.path.join(save_dir, nombre)

    try:
        # Use -t 100 (0.1s) for quicker capture, adjust if needed
        # For 3.5" screens, often preview from libcamera is not desired or helpful here
        # You might need to specify width/height for libcamera-jpeg if it defaults too large
        # e.g., subprocess.run(["libcamera-jpeg", "-n", "-o", ruta, "-t", "100", "--width", "640", "--height", "480"], check=True)
        subprocess.run(["libcamera-jpeg", "-n", "-o", ruta, "-t", "200"], check=True) # -n no preview
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

    # Mostrar la imagen capturada en image_display_label
    try:
        img_pil = Image.open(ruta)
        # Dynamically determine thumbnail size based on left_frame's current size
        # Get actual size of the label where image will be shown
        # Subtract some padding
        max_w = image_display_label.winfo_width() - 10 # Allow 5px padding on each side
        max_h = image_display_label.winfo_height() - 10 # Allow 5px padding on each side

        if max_w <=0 or max_h <=0: # Fallback if winfo_width/height not ready
             max_w = 180 # A reasonable guess for small screen
             max_h = 140

        img_pil.thumbnail((max_w, max_h), Image.LANCZOS) # Use LANCZOS for better quality resize
        tk_image_ref = ImageTk.PhotoImage(img_pil)
        image_display_label.config(image=tk_image_ref, text="")
        root.update_idletasks()
    except Exception as e:
        status_label.config(text=f"Error al mostrar: {e}")
        image_display_label.config(image=None, text="Error img") # Short error for small screen
        tk_image_ref = None

    resultado = classify_image(ruta)
    status_label.config(text=f"Es: {resultado}") # Shorter label

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

    image_display_label.config(image=None, text="imagen", fg="blue")
    tk_image_ref = None

    status_label.config(text="Esperando...")

    foto_button.config(state=tk.NORMAL)
    limpiar_button.config(state=tk.DISABLED)


# --- Interfaz con Tkinter ---
root = tk.Tk()
root.title("Detector") # Shorter title
# Target a common 3.5" resolution. Adjust if yours is different (e.g., 320x240)
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
# Optional: Make the window non-resizable if it's for a fixed display
# root.resizable(False, False)
# Optional: For RPi, sometimes useful to force full screen (uncomment if needed)
# root.attributes('-fullscreen', True)


# Configure root grid
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Main frame using grid to allow expansion
main_frame = tk.Frame(root, padx=2, pady=2) # Reduced padding
main_frame.grid(row=0, column=0, sticky="nsew")

# Configure main_frame's grid (1 row, 2 columns)
main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_columnconfigure(0, weight=3) # Left frame takes more space (e.g. 3 parts)
main_frame.grid_columnconfigure(1, weight=2) # Right frame takes less space (e.g. 2 parts)


# Frame izquierdo para el display de la imagen ("imagen")
left_frame = tk.Frame(main_frame, bd=1, relief=tk.SOLID) # Reduced border
left_frame.grid(row=0, column=0, sticky="nsew", padx=(0,2))

# Configure left_frame's grid (for the image label to fill it)
left_frame.grid_rowconfigure(0, weight=1)
left_frame.grid_columnconfigure(0, weight=1)

image_display_label = tk.Label(left_frame, text="imagen", fg="blue", font=font.Font(size=BASE_FONT_SIZE + 2))
image_display_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)


# Frame derecho para los controles
right_frame = tk.Frame(main_frame, bd=1, relief=tk.SOLID) # Reduced border
right_frame.grid(row=0, column=1, sticky="nsew", padx=(2,0))

# Configure right_frame's grid (status label above, buttons below)
right_frame.grid_rowconfigure(0, weight=1) # Status label container
right_frame.grid_rowconfigure(1, weight=0) # Buttons container (takes only needed space)
right_frame.grid_columnconfigure(0, weight=1)


# Frame para el "campo de texto" (status_label)
status_label_container = tk.Frame(right_frame, bd=1, relief=tk.SOLID) # Reduced border
status_label_container.grid(row=0, column=0, sticky="nsew", pady=(2,2), padx=2)

# Configure status_label_container's grid
status_label_container.grid_rowconfigure(0, weight=1)
status_label_container.grid_columnconfigure(0, weight=1)

status_label = tk.Label(
    status_label_container,
    text="Esperando...",
    font=font.Font(size=BASE_FONT_SIZE),
    wraplength= (SCREEN_WIDTH * 2 // 5) - 20, # Approx width of right_frame - padding
    justify=tk.LEFT,
    anchor="nw"
)
status_label.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)


# Frame para los botones
buttons_container = tk.Frame(right_frame)
buttons_container.grid(row=1, column=0, sticky="ew", pady=2, padx=2)

# Configure buttons_container's grid (for centering or full-width buttons)
buttons_container.grid_columnconfigure(0, weight=1) # Allow button to expand if sticky="ew"

foto_button = tk.Button(
    buttons_container,
    text="foto",
    command=tomar_y_clasificar,
    font=font.Font(size=BASE_FONT_SIZE)
    # height=1 # Often better to let font determine height
)
foto_button.grid(row=0, column=0, sticky="ew", pady=(2,1)) # sticky="ew" makes button fill width

limpiar_button = tk.Button(
    buttons_container,
    text="limpiar",
    command=limpiar_datos,
    font=font.Font(size=BASE_FONT_SIZE)
    # height=1
)
limpiar_button.grid(row=1, column=0, sticky="ew", pady=(1,2))
limpiar_button.config(state=tk.DISABLED)

# Call update_idletasks once before getting widget sizes for the first time
# This helps winfo_width/height in tomar_y_clasificar to have initial values
# though it might still be 0 if called too early before window is fully drawn.
# A more robust way is to bind to <Configure> event for dynamic resizing if needed.
root.update_idletasks()

root.mainloop()