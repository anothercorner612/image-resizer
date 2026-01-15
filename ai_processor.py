import os
import io
from rembg import remove, new_session
from PIL import Image, ImageOps, ImageFilter

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test" 
OUTPUT_FOLDER = "/Users/leefrank/Desktop/showdown_results"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# BiRefNet is essential for your figurines and complex shapes
session = new_session("birefnet-general")

def process_universal():
    # Added .heic for iPhone photos if you have them
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.heic'))]
    
    print(f"📦 Processing Library: {len(files)} items (Universal Mode)")

    for i, img_name in enumerate(files, 1):
        try:
            original = Image.open(os.path.join(INPUT_FOLDER, img_name)).convert("RGBA")
            
            # 1. DOWNSCALE TRICK (Keeps speed high, 1500 is safe for details)
            scale = 1500 / max(original.size)
            if scale < 1:
                low_res_size = (int(original.width * scale), int(original.height * scale))
                prep_img = original.resize(low_res_size, Image.Resampling.LANCZOS)
            else:
                prep_img = original
            
            padding = 100
            prep = ImageOps.expand(prep_img, border=padding, fill=(30, 30, 30))
            prep_bytes = io.BytesIO()
            prep.save(prep_bytes, format='PNG')

            # 2. GENERATE MASK
            mask_data = remove(prep_bytes.getvalue(), session=session, only_mask=True)
            mask = Image.open(io.BytesIO(mask_data)).convert("L")

            # 3. UNIVERSAL REFINEMENT (The "Safe" Logic)
            # MaxFilter(5) fixes white-on-white books
            # MinFilter(5) smooths edges but PRESERVES keychain rings & bike spokes
            mask = mask.filter(ImageFilter.MaxFilter(5)) 
            mask = mask.filter(ImageFilter.MinFilter(5)) 
            mask = mask.filter(ImageFilter.GaussianBlur(radius=1))

            # 4. UPSCALE & APPLY
            mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding))
            mask = mask.resize(original.size, Image.Resampling.LANCZOS)
            
            final = Image.new("RGBA", original.size, (0, 0, 0, 0))
            final.paste(original, (0, 0), mask)

            # 5. CROP, CENTER & SQUARE (1200x1200px)
            bbox = final.getbbox()
            if bbox:
                final = final.crop(bbox)
            
            canvas = Image.new("RGBA", (1200, 1200), (0, 0, 0, 0))
            # Thumbnail to 1100px (leaving 50px margin)
            final.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
            offset = ((1200 - final.width) // 2, (1200 - final.height) // 2)
            canvas.paste(final, offset, final)

            # 6. SAVE
            canvas.save(os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp"), "WEBP", lossless=True)
            print(f"[{i}/{len(files)}] Done: {img_name}          ", end="\r")

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

if __name__ == "__main__":
    process_universal()
