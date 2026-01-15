import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session

# --- CONFIG ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

def surgical_logic(mask_np, strategy):
    """Applies specific 'Intensity' based on the folder."""
    
    # 1. SET INTENSITY
    if strategy == "Complex_Fix":
        trim_strength = 12    # Deep trim for bad backgrounds
        fill_holes = True     # Fixes David Campany text holes
        smooth_blur = 5
    elif strategy == "3D_Objects":
        trim_strength = 2     # Very light trim to keep detail
        fill_holes = True     # Keeps keychains solid
        smooth_blur = 7       # Extra smoothing for jagged edges
    elif strategy == "Wavy_Spreads":
        trim_strength = 5     # Medium trim
        fill_holes = True 
        smooth_blur = 3
    else: # Flat_Paper
        trim_strength = 3     # Standard trim
        fill_holes = True
        smooth_blur = 3

    # 2. APPLY TRIM (Erosion)
    kernel = np.ones((3,3), np.uint8)
    mask_np = cv2.erode(mask_np, kernel, iterations=trim_strength)
    
    # 3. APPLY MATH
    # RETR_EXTERNAL is only used for Paper/Complex to force the outer boundary
    mode = cv2.RETR_EXTERNAL if strategy in ["Flat_Paper", "Complex_Fix"] else cv2.RETR_TREE
    contours, _ = cv2.findContours(mask_np, mode, cv2.CHAIN_APPROX_SIMPLE)
    
    final_mask = np.zeros_like(mask_np)
    if contours:
        cnt = np.concatenate(contours)
        
        if strategy in ["Flat_Paper", "Complex_Fix"]:
            # Forces 90-degree rectangle for books
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect).astype(int)
            cv2.fillPoly(final_mask, [box], 255)
        elif strategy == "Wavy_Spreads":
            # Follows the curves of the pages
            hull = cv2.convexHull(cnt)
            cv2.drawContours(final_mask, [hull], -1, 255, thickness=cv2.FILLED)
        else:
            # Keeps the natural 3D shape of objects
            cv2.drawContours(final_mask, contours, -1, 255, thickness=cv2.FILLED)
            
    # 4. FINAL SMOOTHING
    final_mask = cv2.GaussianBlur(final_mask, (smooth_blur, smooth_blur), 0)
    return final_mask

def run_processor():
    print("🚀 Running Surgical AI Processor...")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    session = new_session("u2net")

    strategies = ["Flat_Paper", "3D_Objects", "Wavy_Spreads", "Complex_Fix"]
    all_files = []
    for s in strategies:
        folder = BASE_INPUT / s
        if folder.exists():
            all_files.extend([(f, s) for f in folder.glob("*") if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']])

    for i, (img_path, strategy) in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] {strategy}: {img_path.name}")
        img = Image.open(img_path).convert("RGB")
        
        # AI Background Removal
        result = remove(img, session=session, alpha_matting=True)
        mask_np = np.array(result.split()[-1]) 

        # Apply Surgical Logic
        refined_mask = surgical_logic(mask_np, strategy)

        # Final Composite
        final_img = img.convert("RGBA")
        final_img.putalpha(Image.fromarray(refined_mask))
        
        # Crop the output
        bbox = final_img.getbbox()
        if bbox:
            final_img = final_img.crop(bbox)
            
        final_img.save(BASE_OUTPUT / f"{img_path.stem}_{strategy}_SURGICAL.png")

if __name__ == "__main__":
    run_processor()
