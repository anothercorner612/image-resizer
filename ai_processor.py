import os
import torch
import numpy as np
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- CONFIG ---
HF_TOKEN = os.getenv("HF_TOKEN")
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/BRIA_PRODUCTION"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Format choice: "PNG" (Classic) or "WEBP" (Modern/Tiny)
OUTPUT_FORMAT = "PNG" 

device = 'mps' if torch.backends.mps.is_available() else 'cpu'
model = AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-2.0', trust_remote_code=True, token=HF_TOKEN).to(device).eval()

def run_production_export(img, base_name):
    # 1. Standard Inference at 1024px
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    input_tensor = transform(img.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        pred = model(input_tensor)[-1].sigmoid().cpu()
    
    mask_np = pred[0].squeeze().numpy()
    
    # 2. Cleanup: Clear background "fog" (anything under 5% opacity)
    mask_np[mask_np < 0.05] = 0
    mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8)).resize(img.size, Image.LANCZOS)
    
    res = img.convert("RGBA")
    res.putalpha(mask_pil)

    # 3. Compression Engine
    save_path = os.path.join(OUTPUT_FOLDER, f"{base_name}.{OUTPUT_FORMAT.lower()}")
    
    if OUTPUT_FORMAT == "WEBP":
        # WebP is natively much smaller
        res.save(save_path, "WEBP", quality=85, method=6)
    else:
        # PNG Optimization: Quantize to 256 colors (P mode) with Alpha
        # This is the "magic" that makes PNGs small
        quantized = res.quantize(colors=256, method=2).convert("RGBA")
        # Put the alpha back after quantization to ensure it's clean
        quantized.putalpha(mask_pil) 
        quantized.save(save_path, "PNG", optimize=True)

    return os.path.getsize(save_path) / 1024 / 1024 # Return MB size

if __name__ == "__main__":
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    for img_name in files:
        base = os.path.splitext(img_name)[0]
        mb = run_production_export(Image.open(os.path.join(INPUT_FOLDER, img_name)), base)
        print(f"✅ {img_name} compressed to: {mb:.2f} MB")
