import os
import io
import webbrowser
from rembg import remove, new_session
from PIL import Image, ImageOps, ImageFilter, ImageChops, ImageDraw

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
BASE_OUTPUT = "/Users/leefrank/Desktop/showdown_results"
os.makedirs(BASE_OUTPUT, exist_ok=True)

# Engines
session_biref = new_session("birefnet-general")
session_u2net = new_session("u2net")

def apply_mask_logic(original, session, strategy):
    padding = 100
    # Strategy D inspired dark padding
    prep = ImageOps.expand(original, border=padding, fill=(30, 30, 30))
    prep_bytes = io.BytesIO()
    prep.save(prep_bytes, format='PNG')
    
    # Generate Base AI Mask
    mask_data = remove(prep_bytes.getvalue(), session=session, only_mask=True)
    mask = Image.open(io.BytesIO(mask_data)).convert("L")
    mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding)).resize(original.size)
    
    if strategy == "RECT_FORCE":
        # Pure geometric protection for rectangular items
        bbox = mask.getbbox()
        if bbox:
            solid = Image.new("L", original.size, 0)
            draw = ImageDraw.Draw(solid)
            # 3px inset to kill background halos
            draw.rectangle([bbox[0]+3, bbox[1]+3, bbox[2]-3, bbox[3]-3], fill=255)
            mask = ImageChops.lighter(mask, solid)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=1))

    elif strategy == "HYBRID_SMART":
        # Morphological Closing: Fill holes, keep shape
        mask = mask.filter(ImageFilter.MaxFilter(5)) 
        mask = mask.filter(ImageFilter.MinFilter(7)) # Stronger erosion to kill white bleeds
        mask = mask.filter(ImageFilter.GaussianBlur(radius=1))

    elif strategy == "SOFT_MATTE":
        # The 'Rescue D' style with alpha matting for smooth magazine curves
        mask_data = remove(prep_bytes.getvalue(), session=session, only_mask=True, 
                           alpha_matting=True, alpha_matting_foreground_threshold=240)
        mask = Image.open(io.BytesIO(mask_data)).convert("L")
        mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding)).resize(original.size)

    final = Image.new("RGBA", original.size, (0, 0, 0, 0))
    final.paste(original, (0, 0), mask)
    if final.getbbox(): final = final.crop(final.getbbox())
    return final

def run_showdown():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]
    
    html_content = """
    <html><head><style>
        body { font-family: sans-serif; background: #1a1a1a; color: white; padding: 20px; }
        .row { display: flex; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #444; padding-bottom: 20px; overflow-x: auto; }
        .img-container { margin-right: 15px; text-align: center; flex-shrink: 0; }
        img { max-width: 300px; height: auto; border: 1px solid #555; 
              background-image: linear-gradient(45deg, #333 25%, transparent 25%), linear-gradient(-45deg, #333 25%, transparent 25%), 
              linear-gradient(45deg, transparent 75%, #333 75%), linear-gradient(-45deg, transparent 75%, #333 75%);
              background-size: 20px 20px; }
        h4 { margin: 5px 0; font-size: 12px; color: #aaa; }
    </style></head><body><h2>🏆 Finalist Showdown</h2>"""

    strategies = {
        "1_BiRef_Hybrid": ("birefnet-general", "HYBRID_SMART"),
        "2_BiRef_Rect": ("birefnet-general", "RECT_FORCE"),
        "3_BiRef_Soft": ("birefnet-general", "SOFT_MATTE"),
        "4_U2Net_Hybrid": ("u2net", "HYBRID_SMART")
    }

    for img_name in files:
        print(f"Processing {img_name}...")
        html_content += f"<div class='row'><div class='img-container'><h4>ORIGINAL</h4><img src='{os.path.join(INPUT_FOLDER, img_name)}'></div>"
        
        orig_img = Image.open(os.path.join(INPUT_FOLDER, img_name)).convert("RGBA")
        
        for label, (model, strat) in strategies.items():
            sess = session_biref if model == "birefnet-general" else session_u2net
            result = apply_mask_logic(orig_img, sess, strat)
            
            # Save variation
            save_name = f"{label}_{img_name}.webp"
            result.save(os.path.join(BASE_OUTPUT, save_name), "WEBP", lossless=True)
            html_content += f"<div class='img-container'><h4>{label}</h4><img src='{save_name}'></div>"
        
        html_content += "</div>"

    html_content += "</body></html>"
    with open(os.path.join(BASE_OUTPUT, "showdown_gallery.html"), "w") as f:
        f.write(html_content)
    webbrowser.open(f"file://{os.path.join(BASE_OUTPUT, 'showdown_gallery.html')}")

if __name__ == "__main__":
    run_showdown()
