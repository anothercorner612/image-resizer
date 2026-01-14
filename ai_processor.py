import os
import io
from rembg import remove, new_session
from PIL import Image, ImageEnhance, ImageOps

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

session = new_session("u2net")

def process_cutouts():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]

    print(f"🚀 Processing {len(files)} full-frame images...")

    for i, img_name in enumerate(files, 1):
        input_path = os.path.join(INPUT_FOLDER, img_name)
        output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp")

        try:
            # 1. Open Original
            original_img = Image.open(input_path).convert("RGBA")
            
            # 2. ADD PADDING (The Fix for Full-Frame)
            # We add 50 pixels of padding so the AI can see the book's corners
            padded_img = ImageOps.expand(original_img, border=50, fill='white')
            
            # 3. BOOST CONTRAST (For the Mask)
            enhancer = ImageEnhance.Contrast(padded_img)
            boosted_img = enhancer.enhance(2.0)
            
            boosted_bytes = io.BytesIO()
            boosted_img.save(boosted_bytes, format='PNG')
            
            # 4. GET THE MASK
            mask_data = remove(
                boosted_bytes.getvalue(), 
                session=session,
                only_mask=True,
                post_process_mask=True
            )
            
            # 5. REMOVE PADDING FROM MASK & APPLY
            mask = Image.open(io.BytesIO(mask_data)).convert("L")
            # Crop the mask back to the original size
            mask = mask.crop((50, 50, mask.width - 50, mask.height - 50))
            
            # Create final transparent image
            final_img = Image.new("RGBA", original_img.size, (0, 0, 0, 0))
            final_img.paste(original_img, (0, 0), mask)

            # AUTO-TRIM
            bbox = final_img.getbbox()
            if bbox:
                final_img = final_img.crop(bbox)
            
            final_img.save(output_path, "WEBP", lossless=True)
            print(f"[{i}/{len(files)}] Success: {img_name}", end="\r")

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

    print(f"\n\n🏁 Done! Full-frame edges should be fixed in '{OUTPUT_FOLDER}'")

if __name__ == "__main__":
    process_cutouts()
