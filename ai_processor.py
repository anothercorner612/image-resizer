import os
import io
from PIL import Image
from rembg import remove, new_session  # Old Engine
from transparent_background import Remover  # New Engine

# --- CONFIG ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/ENGINE_BATTLE"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load both engines
print("⏳ Loading Engines...")
birefnet_session = new_session("birefnet-general")
inspyre_remover = Remover()

def process_battle():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for i, img_name in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Comparing: {img_name}")
        path = os.path.join(INPUT_FOLDER, img_name)
        original = Image.open(path).convert("RGBA")
        base_name = os.path.splitext(img_name)[0]

        # 1. OLD ENGINE (BiRefNet)
        # We run it "Raw" (no filters) to see the engine's true power
        biref_raw = remove(original, session=birefnet_session)
        save_result(biref_raw, f"{base_name}_BIREFNET.webp")

        # 2. NEW ENGINE (InSPyReNet)
        try:
            # We explicitly tell numpy to handle the output before giving it to Pillow
            import numpy as np
            inspyre_result = inspyre_remover.process(original.convert("RGB"), type='rgba')
            
            # Convert the raw array into a proper PIL Image object
            inspyre_rgba = Image.fromarray(np.uint8(inspyre_result)).convert("RGBA")
            
            save_result(inspyre_rgba, f"{base_name}_INSPYRE.webp")
        except Exception as e:
            print(f"InSPyReNet failed on {img_name}: {e}")

def save_result(img, filename):
    # Standard centering/scaling logic
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    canvas = Image.new("RGBA", (1200, 1200), (0, 0, 0, 0))
    img.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
    offset = ((1200 - img.width) // 2, (1200 - img.height) // 2)
    canvas.paste(img, offset, img)
    canvas.save(os.path.join(OUTPUT_FOLDER, filename), "WEBP", lossless=True)

if __name__ == "__main__":
    process_battle()
