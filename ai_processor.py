import os
import io
from rembg import remove, new_session
from PIL import Image

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Using BiRefNet but with a specific override in the remove function
session = new_session("birefnet-general")

def process_cutouts():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]

    print(f"🚀 Attempting 'Heavy' Extraction on {len(files)} files...")

    for i, img_name in enumerate(files, 1):
        input_path = os.path.join(INPUT_FOLDER, img_name)
        output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp")

        print(f"[{i}/{len(files)}] Processing: {img_name}...", end="\r")

        try:
            with open(input_path, 'rb') as inp:
                input_data = inp.read()
                
                # THE OVERRIDE:
                # We are disabling alpha_matting because it's eating your book edges.
                # We are using post_process_mask to seal the ladder holes.
                output_data = remove(
                    input_data, 
                    session=session,
                    alpha_matting=False, 
                    post_process_mask=True
                )
                
                img = Image.open(io.BytesIO(output_data)).convert("RGBA")

                # AUTO-TRIM
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                
                img.save(output_path, "WEBP", lossless=True)

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

    print(f"\n\n🏁 Done. Check results in '{OUTPUT_FOLDER}'")

if __name__ == "__main__":
    process_cutouts()
