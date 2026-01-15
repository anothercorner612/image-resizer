import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session

# --- CONFIG ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

def polish_mask(mask_np, strategy):
    """Removes jagged edges and trims extra background pixels."""
    # 1. Smooth the jittery AI edges
    mask_np = cv2.GaussianBlur(mask_np, (3, 3), 0)
    
    # 2. EROSION: Trims the mask inward by 2 pixels to kill the 'extra background'
    kernel = np.ones((3,3), np.uint8)
    mask_np = cv2.erode(mask_np, kernel, iterations=2)

    # 3. Apply Geometry Math
    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return mask_np
    
    cnt = np.concatenate(contours)
    final_mask = np.zeros_like(mask_np)
    
    if strategy in ["Flat_Paper", "Complex_Fix"]:
        # Perfect 90-degree corners
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)
        cv2.fillPoly(final_mask, [box], 255)
    elif strategy == "Wavy_Spreads":
        # Smooth organic hull
        hull = cv2.convexHull(cnt)
        cv2.drawContours(final_mask, [hull], -1, 255, thickness=cv2.FILLED)
    else:
        # 3D Objects: Keep natural shape but filled solid
        cv2.drawContours(final_mask, contours, -1, 255, thickness=cv2.FILLED)
        
    return final_mask

def run_final_pass():
    print("🚀 Running Final Polish Processor...")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    session = new_session("u2net")

    strategies = ["Flat_Paper", "3D_Objects", "Wavy_Spreads", "Complex_Fix"]
    all_files = []
    for s in strategies:
        folder = BASE_INPUT / s
        if folder.exists():
            all_files.extend([(f, s) for f in folder.glob("*") if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']])

    for i, (img_path, strategy) in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] Polishing: {img_path.name}")
        img = Image.open(img_path).convert("RGB")
        
        # AI Pass with Alpha Matting for cleaner separation
        result = remove(img, session=session, alpha_matting=True)
        mask_np = np.array(result.split()[-1]) 

        # Polish Pass (The Fix for Jagged/Extra pixels)
        refined_mask = polish_mask(mask_np, strategy)

        # Save
        final_img = img.convert("RGBA")
        final_img.putalpha(Image.fromarray(refined_mask))
        final_img.save(BASE_OUTPUT / f"{img_path.stem}_{strategy}_FINAL.png")

if __name__ == "__main__":
    run_final_pass()
