import os
import io
import numpy as np
from rembg import remove, new_session
from PIL import Image, ImageOps

# --- CONFIGURATION ---
input_folder = "/Users/leefrank/Desktop/test"
output_folder = "ai_final_results"
os.makedirs(output_folder, exist_ok=True)

# Try 'isnet-general-use' if the default isn't sharp enough
# 'u2net' is default, 'u2netp' is fast, 'isnet-general-use' is high accuracy
session = new_session("isnet-general-use")

def process_images():
    # Added .webp and case-insensitive check
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic', '.bmp')
    files = [f for f in os.listdir(input_folder) if f.lower().endswith(valid_exts)]

    print(f"🚀 Found {len(files)} images. Starting AI extraction...")

    for img_name in files:
        input_path = os.path.join(input_folder, img_name)
        output_path = os.path.join(output_folder, f"{os.path.splitext(img_name)[0]}_FINAL.png")

        try:
            with open(input_path, 'rb') as i:
                input_data = i.read()
                
                # Apply AI removal using the high-accuracy session
                # alpha_matting=True helps with fine details like ladder rungs
                output_data = remove(
                    input_data, 
                    session=session,
                    alpha_matting=True, 
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=10
                )
                
                img = Image.open(io.BytesIO(output_data)).convert("RGBA")

                # --- 2000x2000 WHITE CANVAS LOGIC ---
                canvas_size = (2000, 2000)
                background = Image.new("RGBA", canvas_size, (255, 255, 255, 255))

                # Resize product to fit 85% of the canvas (1700px)
                # We use ImageOps.contain to preserve aspect ratio perfectly
                img = ImageOps.contain(img, (1700, 1700), Image.Resampling.LANCZOS)

                # Center the product
                off_x = (canvas_size[0] - img.size[0]) // 2
                off_y = (canvas_size[1] - img.size[1]) // 2
                
                background.paste(img, (off_x, off_y), img)
                
                # Save as RGB to flatten the alpha and ensure pure white background
                background.convert("RGB").save(output_path, "PNG")
                print(f"✅ Finished: {img_name}")

        except Exception as e:
            print(f"❌ Error processing {img_name}: {e}")

if __name__ == "__main__":
    process_images()
