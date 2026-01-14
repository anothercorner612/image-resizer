import os
import io
from rembg import remove, new_session
from PIL import Image, ImageEnhance, ImageOps

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts_FINAL"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# We use both models based on your findings
session_biref = new_session("birefnet-general")
session_u2net = new_session("u2net")

def process_final():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]

    print(f"🚀 Processing {len(files)} images with Hybrid Logic...")

    for i, img_name in enumerate(files, 1):
        input_path = os.path.join(INPUT_FOLDER, img_name)
        output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp")

        try:
            original_img = Image.open(input_path).convert("RGBA")
            
            # THE FIX FOR THE WHITE TEXT PHOTO:
            # We add a massive neon green border. This forces the AI to see 
            # the entire white page as an 'object' inside a green room.
            padding = 150 
            prep = ImageOps.expand(original_img, border=padding, fill=(0, 255, 0))
            
            # Slight contrast boost to help define the edge of white pages
            prep = ImageEnhance.Contrast(prep).enhance(1.2)
            
            prep_bytes = io.BytesIO()
            prep.save(prep_bytes, format='PNG')
            
            # HYBRID CHOICE:
            # We'll use U2Net for everything now because your gallery showed 
            # it was the most consistent at not 'gutting' the books.
            mask_data = remove(
                prep_bytes.getvalue(), 
                session=session_u2net, 
                only_mask=True, 
                post_process_mask=True
            )
            
            mask = Image.open(io.BytesIO(mask_data)).convert("L")
            mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding))
            mask = mask.resize(original_img.size)
            
            # Apply to original
            final_img = Image.new("RGBA", original_img.size, (0, 0, 0, 0))
            final_img.paste(original_img, (0, 0), mask)
            
            # Final Trim
            bbox = final_img.getbbox()
            if bbox:
                final_img = final_img.crop(bbox)
            
            final_img.save(output_path, "WEBP", lossless=True)
            print(f"[{i}/{len(files)}] Done: {img_name}           ", end="\r")

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

    print(f"\n\n🏁 Done! Results are in: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    process_final()
