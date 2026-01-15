import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session

# --- CONFIG ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

def surgical_math(mask_np, strategy):
    """Applies exact math logic and trimming per folder requirements."""
    
    # 1. SET INTENSITY & LOGIC
    if strategy == "Complex_Fix":
        trim = 5         # Light trim (U2Net is already precise)
        mode = cv2.RETR_EXTERNAL # IGNORE internal text holes
        blur = 3
    elif strategy == "3D_Objects":
        trim = 2         # Minimal trim to keep 3D texture
        mode = cv2.RETR_TREE     # Keep natural internal lines
        blur = 7         # High blur to fix jagged outlines
    elif strategy == "Wavy_Spreads":
        trim = 6         # Deep trim to kill floor shadows
        mode = cv2.RETR_EXTERNAL
        blur = 3
    else: # Flat_Paper
        trim = 3
        mode = cv2.RETR_EXTERNAL
        blur = 3

    # 2. EROSION: Trims the 'extra background' pixels inward
    kernel = np.ones((3,3), np.uint8)
    mask_np = cv2.erode(mask_np, kernel, iterations=trim)
    
    # 3. GEOMETRY Pass
    contours, _ = cv2.findContours(mask_np, mode, cv2.CHAIN_APPROX_SIMPLE)
    final_mask = np.zeros_like(mask_np)
    
    if contours:
        cnt = np.concatenate(contours)
        if strategy in ["Flat_Paper", "Complex_Fix"]:
            # Redraws the book as a solid rectangle (Forces text holes to close)
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect).astype(int)
            cv2.fillPoly(final_mask, [box], 255)
        elif strategy == "Wavy_Spreads":
            # Shrink-wraps the open pages
            hull = cv2.convexHull(cnt)
            cv2.drawContours(final_mask, [hull], -1, 255, thickness=cv2.FILLED)
        else:
            # 3D Objects: Keep natural shape but filled solid
            cv2.drawContours(final_mask, contours, -1, 255, thickness=cv2.FILLED)
            
    # 4. SMOOTHING: Fixes jagged 'staircase' edges
    return cv2.GaussianBlur(final_mask, (blur, blur), 0)

def run_processor():
    print("🚀 Running Final Restored Multi-Model Processor...")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    
    # Models: U2Net is the heavy-duty 'GreenScreen' engine
    model_std = new_session("u2netp")
    model_heavy = new_session("u2net")

    strategies = ["Flat_Paper", "3D_Objects", "Wavy_Spreads", "Complex_Fix"]
    all_files = []
    for s in strategies:
        folder = BASE_INPUT / s
        if folder.exists():
            all_files.extend([(f, s) for f in folder.glob("*") if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']])

    for i, (img_path, strategy) in enumerate(all_files, 1):
        # The David Campany Fix: Use the heavy model for Complex_Fix only
        active_session = model_heavy if strategy == "Complex_Fix" else model_std
        
        print(f"[{i}/{len(all_files)}] {strategy} (Model: {'Heavy' if strategy=='Complex_Fix' else 'Standard'}): {img_path.name}")
        img = Image.open(img_path).convert("RGB")
        
        # AI Pass
        result = remove(img, session=active_session, alpha_matting=True)
        mask_np = np.array(result.split()[-1]) 

        # Surgical Math Pass
        refined_mask = surgical_math(mask_np, strategy)

        # Composite & Crop
        final_img = img.convert("RGBA")
        final_img.putalpha(Image.fromarray(refined_mask))
        
        bbox = final_img.getbbox()
        if bbox:
            final_img = final_img.crop(bbox)
            
        final_img.save(BASE_OUTPUT / f"{img_path.stem}_{strategy}_FINAL.png")

if __name__ == "__main__":
    run_processor()
