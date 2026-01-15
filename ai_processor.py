import os
from PIL import Image
from transparent_background import Remover  # InSPyReNet
from ben2 import BEN2                       # BEN2

# --- CONFIG ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test_batch"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/BATTLE_RESULTS"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize Engines
print("⏳ Loading InSPyReNet (Standard)...")
inspyre_remover = Remover() 

print("⏳ Loading BEN2 (Boundary Enhanced)...")
ben2_remover = BEN2()
ben2_remover.load_weights()

def save_final(img_rgba, name_suffix, original_name):
    # Tight Crop to product
    bbox = img_rgba.getbbox()
    if bbox:
        img_rgba = img_rgba.crop(bbox)
    
    # Square 1200x1200px centering
    canvas = Image.new("RGBA", (1200, 1200), (0, 0, 0, 0))
    img_rgba.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
    offset = ((1200 - img_rgba.width) // 2, (1200 - img_rgba.height) // 2)
    canvas.paste(img_rgba, offset, img_rgba)
    
    # Save with identifying suffix
    base_name = os.path.splitext(original_name)[0]
    save_path = os.path.join(OUTPUT_FOLDER, f"{base_name}_{name_suffix}.webp")
    canvas.save(save_path, "WEBP", lossless=True)

def run_battle():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for i, img_name in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Processing: {img_name}")
        path = os.path.join(INPUT_FOLDER, img_name)
        original = Image.open(path).convert("RGB")

        # 1. Run InSPyReNet
        try:
            inspyre_raw = inspyre_remover.process(original, type='rgba')
            save_final(Image.fromarray(inspyre_raw), "INSPYRE", img_name)
        except Exception as e:
            print(f"InSPyReNet failed on {img_name}: {e}")

        # 2. Run BEN2
        try:
            ben2_raw, _ = ben2_remover.inference(original)
            save_final(ben2_raw, "BEN2", img_name)
        except Exception as e:
            print(f"BEN2 failed on {img_name}: {e}")

if __name__ == "__main__":
    run_battle()
