import sys, os, io
import numpy as np
import cv2
from PIL import Image
from pathlib import Path

OUTPUT_ROOT = "test_results"
HTML_FILE = "comparison_report.html"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

def process_logic(input_path, image_stem):
    pil_img = Image.open(input_path).convert("RGBA")
    original_np = np.array(pil_img)
    rgb = original_np[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    
    image_results = []

    def save_v(name, alpha_channel):
        res = original_np.copy()
        res[:, :, 3] = alpha_channel
        rel_path = f"{image_stem}_{name}.png"
        Image.fromarray(res).save(os.path.join(OUTPUT_ROOT, rel_path))
        image_results.append((name, rel_path))

    # --- SHARED ASSETS ---
    edges = cv2.Canny(gray, 20, 100)
    wall = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
    
    # 1. BRIGHTNESS SHIELD (Protects White/Gray product parts)
    bright_shield = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY)[1]
    
    # 2. SATURATION SHIELD (Protects colorful product parts)
    sat_shield = cv2.threshold(hsv[:,:,1], 7, 255, cv2.THRESH_BINARY)[1]

    # --- THE 9 VARIATIONS ---

    # OPTIONS 1-3: MASTER HYBRID (Varying Flood Tolerance)
    # Uses the 'Core-Ink' protector to stop black background leaks
    for d in [3, 5, 8]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0, 0, 0] 
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        bg_mask = np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        
        # We protect the inner 90% of the image from 'Ink' deletion
        ink_mask = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)[1]
        core_mask = np.zeros_like(gray)
        cv2.rectangle(core_mask, (width//15, height//15), (width - width//15, height - height//15), 255, -1)
        safe_ink = cv2.bitwise_and(ink_mask, core_mask)
        
        final = cv2.bitwise_or(bg_mask, bright_shield)
        final = cv2.bitwise_or(final, sat_shield)
        final = cv2.bitwise_or(final, safe_ink)
        save_v(f"01_Master_Hybrid_Tol_{d}", final)

    # OPTIONS 4-6: DUAL PASS (Corner-Flood + Variable Shields)
    # Good for trapped background colors
    for s_val in [215, 230, 245]:
        f_m_dual = np.zeros((height + 2, width + 2), np.uint8)
        f_img = rgb.copy()
        f_img[wall == 255] = [0,0,0]
        for pt in [(0,0), (width-1, 0), (0, height-1), (width-1, height-1)]:
            cv2.floodFill(f_img, f_m_dual, pt, (255,255,255), (4,4,4), (4,4,4), 8)
        
        dual_bg = np.where(f_m_dual[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        temp_shield = cv2.threshold(gray, s_val, 255, cv2.THRESH_BINARY)[1]
        save_v(f"02_Dual_Pass_Shield_{s_val}", cv2.bitwise_or(dual_bg, temp_shield))

    # OPTIONS 7-9: "STRICT EDGES" (The 'Wall' logic without the shields)
    # This is for images where the background is very distinct and you don't want any 'glow'
    for d in [4, 10, 16]:
        f_m_strict = np.zeros((height + 2, width + 2), np.uint8)
        temp_strict = rgb.copy()
        # Thick wall iteration
        strict_wall = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=2)
        temp_strict[strict_wall == 255] = [0,0,0]
        cv2.floodFill(temp_strict, f_m_strict, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        save_v(f"03_Strict_Edge_Flood_{d}", np.where(f_m_strict[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8))

    return image_results

def run_comparison(target_path):
    html_content = """<html><head><style>
        body { font-family: sans-serif; background: #000; color: #fff; padding: 20px; }
        .row { display: flex; overflow-x: auto; margin-bottom: 50px; padding: 25px; background: #1a1a1a; border-radius: 15px; }
        .img-card { flex: 0 0 320px; margin-right: 25px; text-align: center; background: #222; padding: 15px; border-radius: 10px; border: 1px solid #333; }
        .img-card img { width: 100%; height: auto; border: 1px solid #444; margin-top: 12px;
            background-image: linear-gradient(45deg, #111 25%, transparent 25%), linear-gradient(-45deg, #111 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #111 75%), linear-gradient(-45deg, transparent 75%, #111 75%);
            background-size: 18px 18px; background-position: 0 0, 0 9px, 9px -9px, -9px 0px; }
        h2 { color: #f1c40f; text-shadow: 1px 1px 2px #000; }
        .orig-box { border: 2px solid #f1c40f !important; }
    </style></head><body><h1>Final 9: Logic Selection Gallery</h1>"""

    if os.path.isdir(target_path):
        images = sorted([f for f in os.listdir(target_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
    else:
        images = [os.path.basename(target_path)]
        target_path = os.path.dirname(target_path)

    for img_name in images:
        full_path = os.path.join(target_path, img_name)
        stem = Path(img_name).stem
        orig_rel = f"{stem}_ORIGINAL.png"
        Image.open(full_path).save(os.path.join(OUTPUT_ROOT, orig_rel))
        results = process_logic(full_path, stem)
        html_content += f"<h2>{img_name}</h2><div class='row'>"
        html_content += f"<div class='img-card'><b>ORIGINAL</b><br><img class='orig-box' src='{OUTPUT_ROOT}/{orig_rel}'></div>"
        for label, path in results:
            html_content += f"<div class='img-card'><b>{label}</b><br><img src='{OUTPUT_ROOT}/{path}'></div>"
        html_content += "</div>"

    html_content += "</body></html>"
    with open(HTML_FILE, "w") as f: f.write(html_content)
    print(f"\n🏁 Finished! Open '{HTML_FILE}' in your browser.")

if __name__ == "__main__":
    if len(sys.argv) > 1: run_comparison(sys.argv[1])
