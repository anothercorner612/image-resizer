import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session

# --- CONFIG ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

def iron_clad_mask(mask_np, strategy):
    """The 'Nuclear Option' for fixing the Campany book and background halos."""
    
    # 1. DEEP TRIM: Cuts 8 pixels into the image to guarantee the background is gone
    kernel = np.ones((3,3), np.uint8)
    mask_np = cv2.erode(mask_np, kernel, iterations=8)
    
    # 2. SMOOTH: Fixes the jagged 3D object edges
    mask_np = cv2.GaussianBlur(mask_np, (5, 5), 0)

    # 3. HOLE FILLING: This is the fix for the David Campany text holes
    # RETR_EXTERNAL tells the AI to ONLY look at the outside edge of the book
    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    final_mask = np.zeros_like(mask_np)
    if contours:
        cnt = np.concatenate(contours)
        if strategy in ["Flat_Paper", "Complex_Fix"]:
            # Forces a perfect 90-degree rectangle (No notches allowed)
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect).astype(int)
            cv2.fillPoly(final_mask, [box], 255)
        else:
            # Fills the entire 3D shape solid (No text punch-through)
            cv2.drawContours(final_mask, contours, -1, 255, thickness=cv2.FILLED)
            
    return final_mask

def run_processor():
    print("🚀 Running Iron-Clad Processor...")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    session = new_session("u2net")

    # This loop will find EVERY file in your folders
    all_files = []
    for s in ["Flat_Paper", "3D_Objects", "Wavy_Spreads", "Complex_Fix"]:
        folder = BASE_INPUT / s
        if folder.exists():
            all_files.extend([(f, s) for f in folder.glob("*") if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']])

    print(f"📊 Found {len(all_files)} images. Starting...")

    for i, (img_path, strategy) in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] Processing {img_path.name}...")
        img = Image.open(img_path).convert("RGB")
        
        # Initial AI Pass
        result = remove(img, session=session, alpha_matting=True)
        mask_np = np.array(result.split()[-1]) 

        # Apply the Iron-Clad Polish
        refined_mask = iron_clad_mask(mask_np, strategy)

        # Final Save
        final_img = img.convert("RGBA")
        final_img.putalpha(Image.fromarray(refined_mask))
        
        # Tight Crop (Removes the extra space around the product)
        bbox = final_img.getbbox()
        if bbox:
            final_img = final_img.crop(bbox)
            
        final_img.save(BASE_OUTPUT / f"{img_path.stem}_IRONCLAD.png")

if __name__ == "__main__":
    run_processor()
