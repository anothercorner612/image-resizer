import os
import io
from rembg import remove, new_session
from PIL import Image

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# BIREFNET-GENERAL is still our best bet for the complicated colors 
# on the book cover and the ladder drawing.
session = new_session("birefnet-general")

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
                
                # We use very light alpha matting. 
                # This helps with the mesh cover but keeps the book edges sharp.
                output_data = remove(
                    input_data, 
                    session=session,
                    alpha_matting=True,
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=2
                )
                
                # Load the result (which is already transparent)
                img = Image.open(io.BytesIO(output_data)).convert("RGBA")

                # --- AUTO-TRIM ---
                # This crops the image to only the non-transparent pixels.
                # If your book is full-frame, this won't change much, 
                # but it ensures no 'ghost' pixels remain at the edges.
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                
                # Save as transparent WebP
                img.save(output_path, "WEBP", lossless=True)

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

    print(f"\n\n🏁 Done! Transparent files are in '{OUTPUT_FOLDER}'")

if __name__ == "__main__":
    process_cutouts()
