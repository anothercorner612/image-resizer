import os
import torch
import numpy as np
import cv2
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- CONFIGURATION ---
HF_TOKEN = "your_token_here"  # <--- Update this
INPUT_FOLDER = "/Users/leefrank/Desktop/test_batch"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/BRIA_FINAL_PRODUCTION"

# SETTINGS
OUTPUT_FORMAT = "WEBP" # Options: "WEBP" (Tiny) or "PNG" (Classic)
FOG_THRESHOLD = 0.05   # Sensitivity for clearing background noise
FORCE_RECTANGLE = True # SET TO TRUE to solve the David Campany/Full-Frame issue

# Create output directory
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Device Selection (M1/M2/M3 Mac = 'mps')
device = 'mps' if torch.backends.mps.is_available() else 'cpu'

# Load Bria 2.0
print("🚀 Loading Bria 2.0...")
model = AutoModelForImageSegmentation.from_pretrained(
    'briaai/RMBG-2.0', 
    trust_remote_code=True, 
    token=HF_TOKEN
).to(device).eval()

def apply_smart_rectangle(orig_img, mask_np):
    """Overrides AI holes by forcing a solid bounding box around the subject."""
    # 1. Binarize the mask (find anything the AI 'thought' was foreground)
    _, binary = cv2.threshold((mask_np * 255).astype(np.uint8), 20, 255, cv2.THRESH_BINARY)
    
    # 2. Find the bounding coordinates of all detected 'bits'
    coords = cv2.findNonZero(binary)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        
        # 3. Create a new solid mask for the rectangle
        # This repairs text/white space holes in the David Campany cover
        final_mask = np.zeros_like(mask_np)
        final_mask[y:y+h, x:x+w] = 1.0
        
        mask_pil = Image.fromarray((final_mask * 255).astype(np.uint8)).resize(orig_img.size, Image.LANCZOS)
    else:
        # Fallback to standard mask if nothing detected
        mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8)).resize(orig_img.size, Image.LANCZOS)
    
    return mask_pil

def process_image(img_path, file_name):
    orig = Image.open(img_path)
    base_name = os.path.splitext(file_name)[0]
    
    # AI Processing
    t = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    input_tensor = t(orig.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    
    mask_np = preds[0].squeeze().numpy()

    # Apply Logic
    if FORCE_RECTANGLE:
        mask_pil = apply_smart_rectangle(orig, mask_np)
    else:
        # Standard Bria logic (clears fog)
        mask_np[mask_np < FOG_THRESHOLD] = 0
        mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8)).resize(orig.size, Image.LANCZOS)
    
    # Create final image
    result = orig.convert("RGBA")
    result.putalpha(mask_pil)

    # Export
    save_path = os.path.join(OUTPUT_FOLDER, f"{base_name}.{OUTPUT_FORMAT.lower()}")
    if OUTPUT_FORMAT == "WEBP":
        result.save(save_path, "WEBP", quality=85, method=6)
    else:
        # PNG Quantization for small file size
        alpha = result.getchannel('A')
        quantized = result.quantize(colors=256, method=2).convert("RGBA")
        quantized.putalpha(alpha)
        quantized.save(save_path, "PNG", optimize=True)
            
    return os.path.getsize(save_path) / 1024 / 1024

if __name__ == "__main__":
    images = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"📂 Found {len(images)} images. Mode: {'RECTANGLE FORCE' if FORCE_RECTANGLE else 'STANDARD'}")
    
    for i, name in enumerate(images):
        try:
            mb = process_image(os.path.join(INPUT_FOLDER, name), name)
            print(f"[{i+1}/{len(images)}] ✅ {name} -> {mb:.2f} MB")
        except Exception as e:
            print(f"❌ Failed {name}: {e}")

    print(f"\n✨ Completed! Files are in: {OUTPUT_FOLDER}")
