import os
import io
import webbrowser
from rembg import remove, new_session
from PIL import Image, ImageEnhance, ImageOps

# --- CONFIGURATION ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
BASE_OUTPUT = "/Users/leefrank/Desktop/transparent_cutouts_FINAL"
os.makedirs(BASE_OUTPUT, exist_ok=True)

# Initialize models
session_biref = new_session("birefnet-general")
session_u2net = new_session("u2net")

# 5 Surgical Strategies + Your 2 Previous Favorites for Reference
STRATEGIES = {
    "Ref_3_U2Net_Green": {"session": session_u2net, "pad": (0, 255, 0), "matt": False, "contrast": 1.5},
    "Ref_5_BiRef_Nat": {"session": session_biref, "pad": (220, 220, 220), "matt": False, "contrast": 1.0},
    "RESCUE_A_Matting": {"session": session_u2net, "pad": (0, 255, 0), "matt": True, "contrast": 1.2},
    "RESCUE_B_Soft_BiRef": {"session": session_biref, "pad": (180, 180, 180), "matt": True, "contrast": 1.0},
    "RESCUE_D_Dark_Silho": {"session": session_biref, "pad": (30, 30, 30), "matt": True, "contrast": 0.8}
}

def build_rescue_gallery():
    valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]
    
    for folder in STRATEGIES.keys():
        os.makedirs(os.path.join(BASE_OUTPUT, folder), exist_ok=True)

    html_content = """
    <html>
    <head>
        <title>Surgical Rescue Gallery</title>
        <style>
            body { font-family: sans-serif; background: #222; color: #fff; padding: 20px; }
            .row { display: flex; margin-bottom: 30px; background: #333; padding: 15px; border-radius: 8px; overflow-x: auto; }
            .card { text-align: center; margin-right: 15px; flex-shrink: 0; }
            img { max-width: 250px; height: auto; border: 1px solid #444; background-image: 
                linear-gradient(45deg, #444 25%, transparent 25%), linear-gradient(-45deg, #444 25%, transparent 25%),
                linear-gradient(45deg, transparent 75%, #444 75%), linear-gradient(-45deg, transparent 75%, #444 75%);
                background-size: 20px 20px; }
            .ref { border: 2px solid #ff9800; padding: 5px; border-radius: 4px; }
            .rescue { border: 2px solid #00e676; padding: 5px; border-radius: 4px; }
            h3 { font-size: 11px; margin: 5px 0; color: #bbb; }
        </style>
    </head>
    <body>
        <h2>Surgical Rescue: Solving the Hard 5%</h2>
        <p>Orange = Previous Favorites | Green = New Surgical Tweaks</p>
    """

    for img_name in files:
        html_content += f"<div class='row'>\n<div class='card'><h3>ORIGINAL</h3><img src='{os.path.join(INPUT_FOLDER, img_name)}'></div>"
        
        for folder, s in STRATEGIES.items():
            try:
                original = Image.open(os.path.join(INPUT_FOLDER, img_name)).convert("RGBA")
                
                # Prep
                padding = 150
                prep = ImageOps.expand(original, border=padding, fill=s['pad'])
                prep = ImageEnhance.Contrast(prep).enhance(s['contrast'])
                
                # Run AI
                prep_bytes = io.BytesIO()
                prep.save(prep_bytes, format='PNG')
                
                mask_data = remove(
                    prep_bytes.getvalue(), session=s['session'], only_mask=True,
                    alpha_matting=s['matt'], 
                    alpha_matting_foreground_threshold=240, 
                    alpha_matting_background_threshold=10,
                    post_process_mask=True
                )
                
                # Process Mask
                mask = Image.open(io.BytesIO(mask_data)).convert("L")
                mask = mask.crop((padding, padding, mask.width - padding, mask.height - padding)).resize(original.size)
                
                final = Image.new("RGBA", original.size, (0, 0, 0, 0))
                final.paste(original, (0, 0), mask)
                
                if final.getbbox(): final = final.crop(final.getbbox())
                
                rel_path = os.path.join(folder, f"{os.path.splitext(img_name)[0]}.webp")
                final.save(os.path.join(BASE_OUTPUT, rel_path), "WEBP", lossless=True)
                
                css_class = "ref" if "Ref" in folder else "rescue"
                html_content += f"<div class='card {css_class}'><h3>{folder}</h3><img src='{rel_path}'></div>"
                
            except Exception as e:
                print(f"Error on {img_name}: {e}")
        
        html_content += "</div>"
        print(f"✅ Comparison built for {img_name}")

    html_content += "</body></html>"
    
    html_path = os.path.join(BASE_OUTPUT, "rescue_gallery.html")
    with open(html_path, "w") as f:
        f.write(html_content)
    
    webbrowser.open(f"file://{html_path}")

if __name__ == "__main__":
    build_rescue_gallery()
