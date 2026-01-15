import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from rembg import remove, new_session

# --- CONFIG ---
BASE_INPUT = Path.home() / "Desktop" / "AI_TEST_INPUT"
BASE_OUTPUT = Path.home() / "Desktop" / "AI_TEST_RESULTS"

def process_image(img_path, strategy, session):
    img = Image.open(img_path).convert("RGB")
    
    # AI Background Removal
    # We use alpha_matting=True to prevent white halos on light covers
    result = remove(img, session=session, alpha_matting=True)
    mask = np.array(result.split()[-1]) 

    # --- THE 3 METHODS ---
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return None
    
    cnt = np.concatenate(contours)
    final_mask = np.zeros_like(mask)

    # METHOD 1: Rotated Rectangle (For Flat Paper & Complex Fix)
    # This ignores holes in the middle (fixing the Campany book text issue)
    if strategy in ["Flat_Paper", "Complex_Fix"]:
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(int)
        cv2.fillPoly(final_mask, [box], 255)

    # METHOD 2: Convex Hull / Shrink Wrap (For Wavy Spreads)
    elif strategy == "Wavy_Spreads":
        hull = cv2.convexHull(cnt)
        cv2.drawContours(final_mask, [hull], -1, 255, thickness=cv2.FILLED)

    # METHOD 3: Standard Cutout (For 3D Objects)
    else:
        cv2.drawContours(final_mask, contours, -1, 255, thickness=cv2.FILLED)

    # Save Result
    output = img.convert("RGBA")
    output.putalpha(Image.fromarray(final_mask))
    return output

def run_all():
    print("🚀 Initializing Full AI Processor...")
    os.makedirs(BASE_OUTPUT, exist_ok=True)
    session = new_session("u2net")
    
    strategies = ["Flat_Paper", "3D_Objects", "Wavy_Spreads", "Complex_Fix"]
    
    for strategy in strategies:
        folder = BASE_INPUT / strategy
        # Updated to catch ALL images in the folder, regardless of count
        files = [f for f in folder.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
        
        print(f"📂 Processing {len(files)} files in {strategy}...")
        
        for f in files:
            processed = process_image(f, strategy, session)
            if processed:
                save_name = f"{f.stem}_{strategy}.png"
                processed.save(BASE_OUTPUT / save_name)
                print(f"  ✅ {save_name} saved.")

if __name__ == "__main__":
    run_all()
