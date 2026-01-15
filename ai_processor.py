import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session

# --- CONFIGURATION ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

# Define our 4 core strategies
STRATEGIES = {
    "Flat_Paper": {"math": "Rotated_Rect"},
    "3D_Objects": {"math": "Standard"},
    "Wavy_Spreads": {"math": "Shrink_Wrap"},
    "Complex_Fix": {"math": "Rotated_Rect"}
}

def apply_rotated_rect(orig_img, mask_np):
    """Forces 90-degree corners for flat items like Calendars and Books."""
    _, binary = cv2.threshold(mask_np, 30, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        all_pts = np.concatenate(contours)
        rect = cv2.minAreaRect(all_pts)
        box = cv2.boxPoints(rect).astype(int)
        clean_mask = np.zeros(mask_np.shape, dtype=np.uint8)
        cv2.fillPoly(clean_mask, [box], 255)
        return Image.fromarray(clean_mask).resize(orig_img.size, Image.LANCZOS)
    return Image.fromarray(mask_np).resize(orig_img.size, Image.LANCZOS)

def apply_shrink_wrap(orig_img, mask_np):
    """Follows the organic curves of open magazine spreads."""
    _, binary = cv2.threshold(mask_np, 20, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        all_pts = np.concatenate(contours)
        hull = cv2.convexHull(all_pts)
        clean_mask = np.zeros(mask_np.shape, dtype=np.uint8)
        cv2.drawContours(clean_mask, [hull], -1, 255, thickness=cv2.FILLED)
        return Image.fromarray(clean_mask).resize(orig_img.size, Image.LANCZOS)
    return Image.fromarray(mask_np).resize(orig_img.size, Image.LANCZOS)

def process_batch():
    print("🚀 Initializing AI Processor (Downloading model on first run...)")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    session = new_session("u2net") # Uses the U2Net model (best for your 'Complex' cases)

    for folder_name, config in STRATEGIES.items():
        folder_path = BASE_INPUT / folder_name
        if not folder_path.exists():
            os.makedirs(folder_path, exist_ok=True)
            print(f"📁 Created folder: {folder_name} (Add images here!)")
            continue

        images = list(folder_path.glob("*.*"))
        if not images:
            print(f"ℹ️ Folder '{folder_name}' is empty. Skipping.")
            continue

        print(f"\n📂 Processing {len(images)} images in {folder_name}...")

        for img_path in images:
            if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']: continue
            
            # 1. AI Background Removal
            input_img = Image.open(img_path)
            output_img = remove(input_img, session=session)
            
            # Get the Alpha channel (the mask) to apply our geometry math
            mask_np = np.array(output_img.split()[-1]) 

            # 2. Apply Specific Math Logic
            if config['math'] == "Rotated_Rect":
                final_mask = apply_rotated_rect(input_img, mask_np)
                print(f"  📐 Applied Rotated Rectangle to {img_path.name}")
            elif config['math'] == "Shrink_Wrap":
                final_mask = apply_shrink_wrap(input_img, mask_np)
                print(f"  🌊 Applied Shrink Wrap to {img_path.name}")
            else:
                final_mask = Image.fromarray(mask_np).resize(input_img.size, Image.LANCZOS)
                print(f"  🍃 Applied Standard Cutout to {img_path.name}")

            # 3. Create Final Image & Save
            final_img = input_img.convert("RGBA")
            final_img.putalpha(final_mask)
            
            save_path = BASE_OUTPUT / f"{img_path.stem}_PROCESSED.webp"
            final_img.save(save_path, "WEBP", quality=90)
            print(f"  ✅ Saved: {save_path.name}")

    print(f"\n✨ All done! Check the 'AI_TEST_RESULTS' folder on your Desktop.")

if __name__ == "__main__":
    process_batch()
