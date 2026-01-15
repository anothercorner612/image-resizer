import os
import io
from rembg import remove, new_session
from PIL import Image, ImageOps, ImageFilter

# Config
INPUT_FOLDER = "/Users/leefrank/Desktop/test" 
OUTPUT_FOLDER = "/Users/leefrank/Desktop/results"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

session = new_session("birefnet-general")

def process():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    for img_name in files:
        try:
            original = Image.open(os.path.join(INPUT_FOLDER, img_name)).convert("RGBA")
            
            # Padding for edge safety
            padding = 100
            prep = ImageOps.expand(original, border=padding, fill=(30, 30, 30))
            prep_bytes = io.BytesIO()
            prep.save(prep_bytes, format='PNG')

            # 1. Generate Raw Mask
            mask_data = remove(prep_bytes.getvalue(), session=session, only_mask=True)
            mask = Image.open(io.BytesIO(mask_data)).convert("L")

            # 2. THE THRESHOLD (The "Fog" Fix)
            # Snaps gray pixels to black so they can't grow into a haze
            mask = mask.point(lambda p: 255 if p > 128 else 0)

            # 3. HYBRID FILTER (The "Mundial" Fix)
            mask = mask.filter(ImageFilter.MaxFilter(5)) # Fills white gaps
            mask = mask.filter(ImageFilter.MinFilter(5)) # Restores edge
            
            # Apply and Save
            mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding))
            final = Image.new("RGBA", original.size, (0, 0, 0, 0))
            final.paste(original, (0, 0), mask)
            
            # Centering on 1200px canvas
            bbox = final.getbbox()
            if bbox:
                final = final.crop(bbox)
            canvas = Image.new("RGBA", (1200, 1200), (0, 0, 0, 0))
            final.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
            offset = ((1200 - final.width) // 2, (1200 - final.height) // 2)
            canvas.paste(final, offset, final)
            canvas.save(os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(img_name)[0]}.webp"), "WEBP", lossless=True)
        except Exception as e:
            print(f"Error {img_name}: {e}")

if __name__ == "__main__":
    process()
