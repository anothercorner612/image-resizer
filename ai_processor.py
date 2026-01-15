import os
import torch
import numpy as np
import cv2
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- CONFIG ---
HF_TOKEN = "your_token_here"
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/SHRINK_WRAP_RESULTS"

# TWEAK THESE TWO
PADDING = 5      # Increase to 5 or 10 if the cutout is "too small"
CONFIDENCE = 20    # Lower (e.g. 10) to catch faint text; Higher (e.g. 50) to ignore floor shadows

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
device = 'mps' if torch.backends.mps.is_available() else 'cpu'

print("🚀 Loading Bria 2.0...")
model = AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-2.0', trust_remote_code=True, token=HF_TOKEN).to(device).eval()

def apply_shrink_wrap(orig_img, mask_np):
    # 1. Find all pixels the AI is even slightly sure about
    _, binary = cv2.threshold((mask_np * 255).astype(np.uint8), CONFIDENCE, 255, cv2.THRESH_BINARY)
    
    # 2. Find the "points" of the object
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Combine all detected pieces into one big point cloud
        all_points = np.concatenate(contours)
        
        # 3. Create the Convex Hull (The "Shrink Wrap")
        hull = cv2.convexHull(all_points)
        
        # 4. Create a solid mask based on that hull
        mask_height, mask_width = mask_np.shape
        hull_mask = np.zeros((mask_height, mask_width), dtype=np.uint8)
        cv2.drawContours(hull_mask, [hull], -1, 255, thickness=cv2.FILLED)
        
        # 5. Optional: Dilate (The "Padding" fix)
        if PADDING > 0:
            kernel = np.ones((PADDING, PADDING), np.uint8)
            hull_mask = cv2.dilate(hull_mask, kernel, iterations=1)
        
        mask_pil = Image.fromarray(hull_mask).resize(orig_img.size, Image.LANCZOS)
    else:
        mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8)).resize(orig_img.size, Image.LANCZOS)
    
    res = orig_img.convert("RGBA")
    res.putalpha(mask_pil)
    return res

if __name__ == "__main__":
    images = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    for i, name in enumerate(images):
        print(f"[{i+1}/{len(images)}] 🧩 Shrink-wrapping: {name}")
        orig = Image.open(os.path.join(INPUT_FOLDER, name))
        
        # AI Pass
        t = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        input_tensor = t(orig.convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            preds = model(input_tensor)[-1].sigmoid().cpu()
        
        # Apply the geometry fix
        final_img = apply_shrink_wrap(orig, preds[0].squeeze().numpy())
        
        # Save
        save_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(name)[0]}_WRAP.webp")
        final_img.save(save_path, "WEBP", quality=85, method=6)

    print(f"\n✨ Done! Results in: {OUTPUT_FOLDER}")
