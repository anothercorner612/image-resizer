import os, io
from rembg import remove, new_session
from PIL import Image

INPUT = "/Users/leefrank/Desktop/test" 
OUTPUT = "/Users/leefrank/Desktop/READY_FOR_STORE"
os.makedirs(OUTPUT, exist_ok=True)
session = new_session("birefnet-general")

for img_name in [f for f in os.listdir(INPUT) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]:
    try:
        original = Image.open(os.path.join(INPUT, img_name)).convert("RGBA")
        # No filters = No Fog. This is the cleanest the engine can be.
        out = remove(original, session=session)
        
        # Centering and Scaling to 1200px
        bbox = out.getbbox()
        if bbox: out = out.crop(bbox)
        canvas = Image.new("RGBA", (1200, 1200), (0, 0, 0, 0))
        out.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
        canvas.paste(out, ((1200 - out.width) // 2, (1200 - out.height) // 2), out)
        
        canvas.save(os.path.join(OUTPUT, f"{os.path.splitext(img_name)[0]}.webp"), "WEBP", lossless=True)
        print(f"✅ {img_name} done.")
    except Exception as e:
        print(f"❌ {img_name} failed: {e}")
