import os
import torch
import numpy as np
import cv2
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- CONFIGURATION ---
HF_TOKEN = "your_token_here" # <--- Update this
INPUT_FOLDER = "test"        # Set to your 'test' folder
OUTPUT_FOLDER = "output_rotated"

# TUNING PARAMETERS
# Increase PADDING (e.g., 5 or 10) if the book edges feel 'chopped off'
# Set PADDING to -5 if you see a sliver of background at the edges
PADDING = 2 

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
device = 'mps' if torch.backends.mps.is_available() else 'cpu'

print(f"🚀 Initializing Bria 2.0 on {device.upper()}...")
model = AutoModelForImageSegmentation.from_pretrained(
    'briaai/RMBG-2.0', 
    trust_remote_code=True, 
    token=HF_TOKEN
).to(device).eval()

def apply_rotated_rectangle(orig_img, mask_np):
    """Finds the best-fitting 4-corner rectangle and fills it solid."""
    # 1. Convert Bria's soft mask to a hard binary mask
    _, binary = cv2.threshold((mask_np * 255).astype(np.uint8), 30, 255, cv2.THRESH_BINARY)
    
    # 2. Find all 'blobs' the AI detected
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Combine all parts (text, central photo, etc.) into one point cloud
        all_points = np.concatenate(contours)
        
        # 3. Calculate the Rotated Bounding Box
        rect = cv2.minAreaRect(all_points)
        box = cv2.boxPoints(rect)
        box = np.int0(box) # Convert coordinates to integers
        
        # 4. Create a fresh solid white mask for the 4 corners
        h, w = mask_np.shape
        clean_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(clean_mask, [box], 255)
        
        # 5. Apply Padding (Dilate to expand, Erode to shrink)
        if PADDING != 0:
            kernel = np.ones((abs(PADDING), abs(PADDING)), np.uint8)
            if PADDING > 0:
                clean_mask = cv2.dilate(clean_mask, kernel, iterations=1)
            else:
                clean_mask = cv2.erode(clean_mask, kernel, iterations=1)
        
        mask_pil = Image.fromarray(clean_mask).resize(orig_img.size, Image.LANCZOS)
    else:
        # Fallback to standard mask if nothing is detected
        mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8)).resize(orig_img.size, Image.LANCZOS)
    
    # Apply mask to original
    res = orig_img.convert("RGBA")
    res.putalpha(mask_pil)
    return res

def run_batch():
    if not os.path.exists(INPUT_FOLDER):
        print(f"❌ Error: Folder '{INPUT_FOLDER}' not found.")
        return

    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"📂 Found {len(files)} images in '{INPUT_FOLDER}'")

    for i, name in enumerate(files):
        img_path = os.path.join(INPUT_FOLDER, name)
        orig = Image.open(img_path)
        
        # AI Segmentation Pass
        t = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        input_tensor = t(orig.convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            preds = model(input_tensor)[-1].sigmoid().cpu()
        
        # Apply Rotated Rectangle Logic
        final_img = apply_rotated_rectangle(orig, preds[0].squeeze().numpy())
        
        # Save as high-quality WebP
        save_name = os.path.splitext(name)[0] + ".webp"
        final_img.save(os.path.join(OUTPUT_FOLDER, save_name), "WEBP", quality=90, method=6)
        print(f"[{i+1}/{len(files)}] processed: {name}")

if __name__ == "__main__":
    run_batch()
    print(f"\n✨ All set. Check your results in: {OUTPUT_FOLDER}")
