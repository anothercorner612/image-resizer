import os
from pathlib import Path
from PIL import Image

# --- CONFIG ---
# This looks for the folder on your Desktop
BASE_DIR = Path.home() / "Desktop" / "AI_TEST_INPUT"
OUT_DIR = Path.home() / "Desktop" / "AI_TEST_RESULTS"
os.makedirs(OUT_DIR, exist_ok=True)

def run_test_run():
    print("🚀 Starting Test Run: Analyzing files...")
    
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir(): continue
        folder_tag = folder.name.upper()

        for img_path in folder.glob("*.*"):
            if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']: continue
            
            # --- AUTO-DETECTION LOGIC ---
            filename = img_path.name.upper()
            
            # 1. Check for "Complex" Keywords first (The Safety Net)
            if any(word in filename for word in ["CAMPANY", "LADDER", "WHITE", "CREAM"]):
                method = "Complex_Fix (U2Net + Fusion)"
            
            # 2. Check for "Wavy" Keywords
            elif any(word in filename for word in ["SPREAD", "OPEN", "MIDDLE", "INSIDE"]):
                method = "Wavy_Spread (BiRefNet + ShrinkWrap)"
            
            # 3. Categorize by Folder Strategy
            elif "PAPER" in folder_tag:
                method = "Flat_Paper (Bria 2.0 + RotatedRect)"
                
            elif "3D" in folder_tag or "OBJECT" in folder_tag:
                method = "3D_Object (Bria 2.0 + Standard)"
                
            else:
                method = "Standard_Default"

            print(f"📸 {img_path.name} -> Detected as: {method}")
            # Here is where the actual AI call would go:
            # process_image(img_path, method)

if __name__ == "__main__":
    run_test_run()
