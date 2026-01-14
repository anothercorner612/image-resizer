import os
import io
from rembg import remove, new_session
from PIL import Image, ImageEnhance, ImageOps

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "transparent_cutouts"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# U2NET is best for finding the 'shape' in low-contrast shots
session = new_session("u2net")

def is_full_frame(img):
    """Detects if the product touches edges or has a solid color background."""
    width, height = img.size
    # Check 5-pixel strips at the edges
    edges = [
        img.crop((0, 0, width, 5)),
        img.crop((0, height-5, width, height)),
        img.crop((0, 0, 5, height)),
        img.crop((width-5, 0, width, height))
    ]
    for edge in edges:
        # Get color range. If range is high, it's a full-frame image.
        # If range is very low, it's a solid background (black or white).
        stat = edge.convert("L").getextrema()
        diff = stat[1] - stat[0]
        if diff > 40: # High detail at edge = Full Frame
            return True
    return False

def process_cutouts():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]

    print(f"🚀 Processing {len(files)} images (Handling Black/White backgrounds)...")

    for i, img_name in enumerate(files, 1):
        input_path = os.path.join(INPUT_FOLDER, img_name)
        output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp")

        try:
            original_img = Image.open(input_path).convert("RGBA")
            
            # 1. Determine Padding Strategy
            # If full frame, we add padding to create an artificial 'edge'
            full_frame = is_full_frame(original_img)
            padding = 100 if full_frame else 20 
            
            # 2. Prepare the AI 'Tracing' Image
            # We use a neutral gray background for padding to help with both Black and White products
            prep_img = ImageOps.expand(original_img, border=padding, fill=(128, 128, 128))
            
            # 3. Crank Contrast to reveal edge shadows
            enhancer = ImageEnhance.Contrast(prep_img)
            boosted_img = enhancer.enhance(2.5) 
            
            boosted_bytes = io.BytesIO()
            boosted_img.save(boosted_bytes, format='PNG')
            
            # 4. Generate Mask
            mask_data = remove(
                boosted_bytes.getvalue(), 
                session=session,
                only_mask=True,
                post_process_mask=True
            )
            
            # 5. Clean up Mask & Apply to Original
            mask = Image.open(io.BytesIO(mask_data)).convert("L")
            # Remove the padding we added
            mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding))
            mask = mask.resize(original_img.size)
            
            final_img = Image.new("RGBA", original_img.size, (0, 0, 0, 0))
            final_img.paste(original_img, (0, 0), mask)

            # 6. Final Trim
            bbox = final_img.getbbox()
            if bbox:
                final_img = final_img.crop(bbox)
            
            final_img.save(output_path, "WEBP", lossless=True)
            print(f"[{i}/{len(files)}] Done: {img_name}", end="\r")

        except Exception as e:
            print(f"\n❌ Error on {img_name}: {e}")

    print(f"\n\n🏁 Batch Complete!")

if __name__ == "__main__":
    process_cutouts()
