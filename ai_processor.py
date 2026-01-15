import os
import io
from rembg import remove, new_session
from PIL import Image, ImageOps, ImageChops, ImageDraw

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts_RECTANGLE_FORCE"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# BiRefNet is better at finding the initial 'extreme' corners
session = new_session("birefnet-general")

def process_rectangle_force():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]

    print(f"📐 Applying Rectangle Force to {len(files)} images...")

    for i, img_name in enumerate(files, 1):
        try:
            original = Image.open(os.path.join(INPUT_FOLDER, img_name)).convert("RGBA")
            
            # 1. PREP WITH DARK PADDING (Strategy D style)
            padding = 100
            prep = ImageOps.expand(original, border=padding, fill=(30, 30, 30))
            
            prep_bytes = io.BytesIO()
            prep.save(prep_bytes, format='PNG')
            
            # 2. GET INITIAL AI MASK
            mask_data = remove(prep_bytes.getvalue(), session=session, only_mask=True)
            mask = Image.open(io.BytesIO(mask_data)).convert("L")
            mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding)).resize(original.size)

            # 3. RECTANGLE FORCE LOGIC
            # This finds the bounding box of the magazine/page
            bbox = mask.getbbox()
            if bbox:
                # Create a perfectly solid white rectangle based on the bbox
                # We add a 2px 'buffer' to fix the top erosion
                left, top, right, bottom = bbox
                solid_rect = Image.new("L", original.size, 0)
                draw = ImageDraw.Draw(solid_rect)
                draw.rectangle([left-2, top-2, right+2, bottom+2], fill=255)
                
                # Combine the AI's detection with our solid rectangle
                # 'Lighter' takes the maximum value (White > Black)
                mask = ImageChops.lighter(mask, solid_rect)

            # 4. FINAL ASSEMBLY
            final = Image.new("RGBA", original.size, (0, 0, 0, 0))
            final.paste(original, (0, 0), mask)
            
            # Crop to the new forced rectangle
            final_bbox = final.getbbox()
            if final_bbox:
                final = final.crop(final_bbox)
            
            final.save(os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp"), "WEBP", lossless=True)
            print(f"[{i}/{len(files)}] Rect-Forced: {img_name}          ", end="\r")

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

if __name__ == "__main__":
    process_rectangle_force()
