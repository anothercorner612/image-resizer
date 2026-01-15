import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session

# --- CONFIG ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

def clean_mask(mask_np, strategy):
    """Refines the mask to remove halos and artifacts."""
    # 1. Fill small holes (prevents text from being punched out)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    mask_np = cv2.morphologyEx(mask_np, cv2.MORPH_CLOSE, kernel)
    
    # 2. Erosion (Trims the edge by 2 pixels to remove white halos)
    mask_np = cv2.erode(mask_np, kernel, iterations=1)

    # 3. Apply Geometry Math
    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return mask_np
    
    cnt = np.concatenate(contours)
    new_mask = np.zeros_like(mask_np)
    
    if strategy in ["Flat_Paper", "Complex_Fix"]:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)
        cv2.fillPoly(new_mask, [box], 255)
    elif strategy == "Wavy_Spreads":
        hull = cv2.convexHull(cnt)
        cv2.drawContours(new_mask, [hull], -1, 255, thickness=cv2.FILLED)
    else:
        # Standard: Just use the cleaned-up AI mask
        new_mask = mask_np
        
    return new_mask

def run_processor():
    print("🚀 Running Quality-Boost Processor...")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    session = new_session("u2net") # Best all-rounder

    for strategy in ["Flat_Paper", "3D_Objects", "Wavy_Spreads", "Complex_Fix"]:
        folder_path = BASE_INPUT / strategy
        images = list(folder_path.glob("*.*"))
        if not images: continue

        for img_path in images:
            if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png']: continue
            
            img = Image.open(img_path).convert("RGB")
            
            # Use Alpha Matting for smoother edges
            result = remove(img, session=session, alpha_matting=True, 
                            alpha_matting_foreground_threshold=240,
                            alpha_matting_background_threshold=10)
            
            mask = np.array(result.split()[-1])
            refined_mask = clean_mask(mask, strategy)

            # Re-apply refined mask
            final_img = img.convert("RGBA")
            final_img.putalpha(Image.fromarray(refined_mask))
            
            save_name = f"{img_path.stem}_{strategy}.png"
            final_img.save(BASE_OUTPUT / save_name)
            print(f"  ✨ Refined & Saved: {save_name}")

if __name__ == "__main__":
    run_processor()
