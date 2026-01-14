import os
import io
import webbrowser
from rembg import remove, new_session
from PIL import Image, ImageEnhance, ImageOps

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
BASE_OUTPUT = "/Users/leefrank/Desktop/test_variations"
os.makedirs(BASE_OUTPUT, exist_ok=True)

# Initialize models
session_biref = new_session("birefnet-general")
session_u2net = new_session("u2net")

STRATEGIES = {
    "1_BiRef_Dimmed": {"session": session_biref, "bright": 0.8, "contrast": 1.0, "pad_color": (200, 200, 200)},
    "2_BiRef_HighContrast": {"session": session_biref, "bright": 1.0, "contrast": 2.0, "pad_color": (128, 128, 128)},
    "3_U2Net_GreenScreen": {"session": session_u2net, "bright": 1.0, "contrast": 1.5, "pad_color": (0, 255, 0)},
    "4_U2Net_WhiteOut": {"session": session_u2net, "bright": 1.2, "contrast": 2.5, "pad_color": (255, 255, 255)},
    "5_BiRef_Natural": {"session": session_biref, "bright": 1.0, "contrast": 1.0, "pad_color": (220, 220, 220)}
}

def process_and_generate_html():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]
    
    for folder in STRATEGIES.keys():
        os.makedirs(os.path.join(BASE_OUTPUT, folder), exist_ok=True)

    html_content = """
    <html>
    <head>
        <title>Cutout Variation Gallery</title>
        <style>
            body { font-family: sans-serif; background: #f0f0f0; padding: 20px; }
            .row { display: flex; margin-bottom: 40px; background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); overflow-x: auto; }
            .card { text-align: center; margin-right: 15px; flex-shrink: 0; }
            img { max-width: 250px; height: auto; border: 1px solid #ddd; background-image: 
                linear-gradient(45deg, #eee 25%, transparent 25%), linear-gradient(-45deg, #eee 25%, transparent 25%),
                linear-gradient(45deg, transparent 75%, #eee 75%), linear-gradient(-45deg, transparent 75%, #eee 75%);
                background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px; }
            h3 { font-size: 14px; color: #333; margin-bottom: 5px; }
            h2 { border-bottom: 2px solid #333; padding-bottom: 10px; }
        </style>
    </head>
    <body>
        <h2>Product Cutout Strategy Comparison</h2>
    """

    for img_name in files:
        html_content += f"<div class='row'>\n<div class='card'><h3>ORIGINAL</h3><img src='{os.path.join(INPUT_FOLDER, img_name)}'></div>"
        
        for folder, settings in STRATEGIES.items():
            try:
                original_img = Image.open(os.path.join(INPUT_FOLDER, img_name)).convert("RGBA")
                
                # Apply Prep Logic
                padding = 100
                prep = ImageOps.expand(original_img, border=padding, fill=settings['pad_color'])
                prep = ImageEnhance.Brightness(prep).enhance(settings['bright'])
                prep = ImageEnhance.Contrast(prep).enhance(settings['contrast'])
                
                prep_bytes = io.BytesIO()
                prep.save(prep_bytes, format='PNG')
                
                # Run AI
                mask_data = remove(prep_bytes.getvalue(), session=settings['session'], only_mask=True, post_process_mask=True)
                
                # Apply to original
                mask = Image.open(io.BytesIO(mask_data)).convert("L")
                mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding)).resize(original_img.size)
                final_img = Image.new("RGBA", original_img.size, (0, 0, 0, 0))
                final_img.paste(original_img, (0, 0), mask)
                
                # Crop and Save
                bbox = final_img.getbbox()
                if bbox: final_img = final_img.crop(bbox)
                
                rel_path = os.path.join(folder, f"{os.path.splitext(img_name)[0]}.webp")
                final_img.save(os.path.join(BASE_OUTPUT, rel_path), "WEBP", lossless=True)
                
                html_content += f"<div class='card'><h3>{folder}</h3><img src='{rel_path}'></div>"
                
            except Exception as e:
                print(f"Error on {img_name}: {e}")
        
        html_content += "</div>"
        print(f"✅ Processed all variations for {img_name}")

    html_content += "</body></html>"
    
    html_path = os.path.join(BASE_OUTPUT, "gallery.html")
    with open(html_path, "w") as f:
        f.write(html_content)
    
    print(f"\n🏁 ALL DONE. Opening Gallery...")
    webbrowser.open(f"file://{html_path}")

if __name__ == "__main__":
    process_and_generate_html()
