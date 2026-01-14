import os
import io
from rembg import remove, new_session
from PIL import Image, ImageEnhance, ImageOps, ImageFilter

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts_FINAL_RESCUE"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Using BiRefNet as it was the engine for Strategy D
session = new_session("birefnet-general")

def process_final_specialist():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]

    print(f"🚀 Running Final Specialist (Strategy D + Bleed Fix) on {len(files)} images...")

    for i, img_name in enumerate(files, 1):
        input_path = os.path.join(INPUT_FOLDER, img_name)
        output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp")

        try:
            original = Image.open(input_path).convert("RGBA")
            
            # 1. DARK SILHOUETTE PADDING (The Strategy D base)
            # We use a very dark grey (30,30,30) to make white edges pop
            padding = 150
            prep = ImageOps.expand(original, border=padding, fill=(30, 30, 30))
            
            # 2. BLEED PREVENTION
            # We slightly DIM the image before the AI sees it. 
            # This makes the "top bleed" area slightly more distinct from the background.
            prep = ImageEnhance.Brightness(prep).enhance(0.9)
            
            prep_bytes = io.BytesIO()
            prep.save(prep_bytes, format='PNG')
            
            # 3. GENERATE MASK WITH SOFT EDGES
            mask_data = remove(
                prep_bytes.getvalue(),
                session=session,
                only_mask=True,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                post_process_mask=True
            )
            
            # 4. MASK DILATION (The Secret Sauce for Bleeding)
            mask = Image.open(io.BytesIO(mask_data)).convert("L")
            # We "grow" the mask by 2 pixels to recover any 'bleeding' edges
            mask = mask.filter(ImageFilter.MaxFilter(3)) 
            
            # 5. RESTORE SIZE
            mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding))
            mask = mask.resize(original.size)
            
            # 6. APPLY TO ORIGINAL
            final = Image.new("RGBA", original.size, (0, 0, 0, 0))
            final.paste(original, (0, 0), mask)
            
            # Final Trim
            bbox = final.getbbox()
            if bbox:
                final = final.crop(bbox)
            
            final.save(output_path, "WEBP", lossless=True)
            print(f"[{i}/{len(files)}] Success: {img_name}          ", end="\r")

        except Exception as e:
            print(f"\n❌ Failed on {img_name}: {e}")

    print(f"\n\n🏁 Done! Results are in: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    process_final_specialist()
