import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session
import warnings

# Hide those annoying math warnings
warnings.filterwarnings("ignore")

# --- CONFIG ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

def surgical_math(mask_np, strategy):
    """Specific trimming and smoothing for each folder."""
    if strategy == "Complex_Fix":
        trim, mode, blur = 5, cv2.RETR_EXTERNAL, 3
    elif strategy == "3D_Objects":
        trim, mode, blur = 2, cv2.RETR_TREE, 7
    elif strategy == "Wavy_Spreads":
        trim, mode, blur = 6, cv2.RETR_EXTERNAL, 3
    else: # Flat_Paper
        trim, mode, blur = 3, cv2.RETR_EXTERNAL, 3

    # 1. TRIM: Faster than alpha matting
    kernel = np.ones((3,3), np.uint8)
    mask_np = cv2.erode(mask_np, kernel, iterations=trim)
    
    # 2. GEOMETRY
    contours, _ = cv2.findContours(mask_np, mode, cv2.CHAIN_APPROX_SIMPLE)
    final_mask = np.zeros_like(mask_np)
    
    if contours:
        cnt = np.concatenate(contours)
        if strategy in ["Flat_Paper", "Complex_Fix"]:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect).astype(int)
            cv2.fillPoly(final_mask, [box], 255)
        elif strategy == "Wavy_Spreads":
            hull = cv2.convexHull(cnt)
            cv2.drawContours(final_mask, [hull], -1, 255, thickness=cv2.FILLED)
        else:
            cv2.drawContours(final_mask, contours, -1, 255, thickness=cv2.FILLED)
            
    return cv2.GaussianBlur(final_mask, (blur, blur), 0)

def run_processor():
    print("🚀 Running High-Speed Multi-Model Processor...")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    
    # Keep the Heavy model for David Campany and Standard for the rest
    model_std = new_session("u2netp")
    model_heavy = new_session("u2net")

    strategies = ["Flat_Paper", "3D_Objects", "Wavy_Spreads", "Complex_Fix"]
    all_files = []
    for s in strategies:
        folder = BASE_INPUT / s
        if folder.exists():
            all_files.extend([(f, s) for f in folder.glob("*") if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']])

    print(f"📊 Found {len(all_files)} images. Starting high-speed run...")

    for i, (img_path, strategy) in enumerate(all_files, 1):
        active_session = model_heavy if strategy == "Complex_Fix" else model_std
        
        print(f"[{i}/{len(all_files)}] Processing {img_path.name}...")
        
        img = Image.open(img_path).convert("RGB")
        
        # KEY CHANGE: alpha_matting=False for 10x speed boost
        result = remove(img, session=active_session, alpha_matting=False)
        mask_np = np.array(result.split()[-1]) 

        refined_mask = surgical_math(mask_np, strategy)

        final_img = img.convert("RGBA")
        final_img.putalpha(Image.fromarray(refined_mask))
        
        bbox = final_img.getbbox()
        if bbox:
            final_img = final_img.crop(bbox)
            
        final_img.save(BASE_OUTPUT / f"{img_path.stem}_{strategy}_FINAL.png")

if __name__ == "__main__":
    run_processor()
