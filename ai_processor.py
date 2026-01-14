import os
import io
from rembg import remove, new_session
from PIL import Image

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ISNET-GENERAL-USE is often the 'rescue' model for when u2net fails.
# It treats the entire object as a more cohesive unit.
print("📡 Switching to ISNET-GENERAL-USE...")
session = new_session("isnet-general-use")

def process_cutouts():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]

    print(f"🚀 Processing {len(files)} cutouts...")

    for i, img_name in enumerate(files, 1):
        input_path = os.path.join(INPUT_FOLDER, img_name)
        output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp")

        print(f"[{i}/{len(files)}] Extracting: {img_name}...", end="\r")

        try:
            with open(input_path, 'rb') as inp:
                input_data = inp.read()
                
                # We stay with these settings but on the new model.
                output_data = remove(
                    input_data, 
                    session=session,
                    alpha_matting=False,
                    post_process_mask=True
                )

                img = Image.open(io.BytesIO(output_data)).convert("RGBA")

                # --- AUTO-TRIM ---
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                
                img.save(output_path, "WEBP", lossless=True)

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

    print(f"\n\n🏁 Done! Transparent files are in '{OUTPUT_FOLDER}'")

if __name__ == "__main__":
    process_cutouts()
