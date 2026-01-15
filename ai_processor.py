import os
import torch
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- CONFIG ---
HF_TOKEN = os.getenv("HF_TOKEN")
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
BASE_OUTPUT = "/Users/leefrank/Desktop/BRIA_COMPARISON"

# Subfolders for the two runs
FOLDERS = {
    "standard": os.path.join(BASE_OUTPUT, "BRIA_STANDARD"),
    "optimized": os.path.join(BASE_OUTPUT, "BRIA_OPTIMIZED")
}
for f in FOLDERS.values(): os.makedirs(f, exist_ok=True)

device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"🚀 Initializing on {device.upper()}...")

# Load Model
model = AutoModelForImageSegmentation.from_pretrained(
    'briaai/RMBG-2.0', trust_remote_code=True, token=HF_TOKEN
).to(device).eval()

# --- RUN 1: STANDARD (No Adjustments) ---
def run_standard(img):
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    input_tensor = transform(img.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    mask = transforms.ToPILImage()(preds[0].squeeze()).resize(img.size)
    res = img.convert("RGBA")
    res.putalpha(mask)
    return res

# --- RUN 2: OPTIMIZED (Contrast + Threshold + Dilation) ---
def run_optimized(img):
    # 1. Adaptive Contrast Pre-pass
    enhancer = ImageEnhance.Contrast(img)
    detection_img = enhancer.enhance(1.4) # Makes the 'edge' more obvious to the AI
    
    # 2. Inference at 768px (Focuses on object shape, ignores micro-noise)
    transform = transforms.Compose([
        transforms.Resize((768, 768)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    input_tensor = transform(detection_img.convert("RGB")).unsqueeze(0).to(device)
    
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    
    mask_np = preds[0].squeeze().numpy()
    
    # 3. Alpha Thresholding (Kills the gray 'fog' completely)
    mask_binary = (mask_np > 0.35).astype(np.uint8) * 255
    
    # 4. OpenCV-based Dilation (Recovers edges of white pages)
    kernel = np.ones((3, 3), np.uint8)
    mask_refined = cv2.dilate(mask_binary, kernel, iterations=1)
    
    mask_pil = Image.fromarray(mask_refined).resize(img.size, Image.LANCZOS)
    res = img.convert("RGBA")
    res.putalpha(mask_pil)
    return res

def start_comparison():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for img_name in files:
        print(f"⚔️ Battling: {img_name}")
        path = os.path.join(INPUT_FOLDER, img_name)
        original = Image.open(path)
        base = os.path.splitext(img_name)[0]

        # Process Standard
        std_res = run_standard(original)
        std_res.save(os.path.join(FOLDERS["standard"], f"{base}_STD.png"))

        # Process Optimized
        opt_res = run_optimized(original)
        opt_res.save(os.path.join(FOLDERS["optimized"], f"{base}_OPT.png"))

if __name__ == "__main__":
    start_comparison()
    print(f"\n🏁 Finished! Open {BASE_OUTPUT} to compare.")
