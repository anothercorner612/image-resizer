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
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    height, width = gray.shape
    
    image_results = []

    def save_v(name, alpha_channel):
        res = original_np.copy()
        res[:, :, 3] = alpha_channel
        rel_path = f"{image_stem}_{name}.png"
        Image.fromarray(res).save(os.path.join(OUTPUT_ROOT, rel_path))
        image_results.append((name, rel_path))

    # --- ASSET PREP ---
    edges = cv2.Canny(gray, 20, 100)
    wall = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
    
    # SHIELDS (To protect the white/gray product parts)
    bright_shield = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY)[1]
    sat_shield = cv2.threshold(hsv[:,:,1], 5, 255, cv2.THRESH_BINARY)[1]
    # The 'Full Shield' protects anything bright OR colorful
    product_shield = cv2.bitwise_or(bright_shield, sat_shield)

    # --- 1. THE WINNING BASE: EDGE-FLOOD (4-28 Tolerance) ---
    # 6 Variations
    for d in [4, 6, 10, 15, 20, 28]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0, 0, 0] 
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        save_v(f"01_edge_flood_raw_tol_{d}", np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8))

    # --- 2. THE PROTECTED FLOOD (Flood + White Shield) ---
    # This prevents the 'hollow center' on white/gray products
    # 6 Variations
    for d in [4, 8, 12, 16, 20, 25]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0, 0, 0] 
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        raw_flood = np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        # FORCE the shield areas to stay opaque
        final_protected = cv2.bitwise_or(raw_flood, product_shield)
        save_v(f"02_protected_flood_tol_{d}", final_protected)

    # --- 3. LAB CHANNEL PROTECTION (Yellow/Pink Specialist) ---
    # Specifically targets the background color of the ladder photo
    # 6 Variations
    l_c, a_c, b_c = cv2.split(lab)
    # Background distance from neutral gray in LAB space
    bg_color_lab = lab[5, 5].astype(int)
    for l_tol in [10, 20, 30, 40, 50, 60]:
        diff_lab = cv2.absdiff(lab, bg_color_lab)
        _, l_mask = cv2.threshold(cv2.max(diff_lab[:,:,1], diff_lab[:,:,2]), l_tol, 255, cv2.THRESH_BINARY)
        save_v(f"03_lab_color_distance_{l_tol}", l_mask)

    # --- 4. THE 'SMART-HYBRID' (Ink + Sat + Flood) ---
    # 5 Variations
    dark_ink = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)[1]
    for d in [4, 12]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        cv2.floodFill(rgb.copy(), f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        f_mask = np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        # Keep if (NOT background) OR (is dark ink) OR (is colorful)
        hybrid = cv2.bitwise_or(f_mask, cv2.bitwise_or(dark_ink, sat_shield))
        save_v(f"04_smart_hybrid_tol_{d}", hybrid)

    # --- 5. MORPHOLOGICAL REPAIR ---
    # Takes your favorite edge_flood_4 and 'heals' small holes
    _, base_f = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((5,5), np.uint8)
    repaired = cv2.morphologyEx(base_f, cv2.MORPH_CLOSE, kernel)
    save_v("05_morph_repaired_holes", repaired)

    return image_results

def run_comparison(target_path):
    html_content = """<html><head><style>
        body { font-family: sans-serif; background: #111; color: #eee; padding: 20px; }
        .row { display: flex; overflow-x: auto; margin-bottom: 40px; padding: 20px; background: #222; border-radius: 12px; border: 1px solid #444; }
        .img-card { flex: 0 0 300px; margin-right: 20px; text-align: center; background: #333; padding: 12px; border-radius: 8px; }
        .img-card img { width: 100%; height: auto; border: 1px solid #555; margin-top: 10px;
            background-image: linear-gradient(45deg, #222 25%, transparent 25%), linear-gradient(-45deg, #222 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #222 75%), linear-gradient(-45deg, transparent 75%, #222 75%);
            background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px; }
        h2 { color: #00d2ff; margin-top: 40px; font-size: 1.5em; text-transform: uppercase; letter-spacing: 1px; }
        .orig { border: 2px solid #00d2ff !important; }
    </style></head><body><h1>Edge-Flood & Protection Lab</h1>"""

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
        html_content += f"<h2>Product: {img_name}</h2><div class='row'>"
        html_content += f"<div class='img-card'><b>ORIGINAL SOURCE</b><br><img class='orig' src='{OUTPUT_ROOT}/{orig_rel}'></div>"
        for label, path in results:
            html_content += f"<div class='img-card'><b>{label}</b><br><img src='{OUTPUT_ROOT}/{path}'></div>"
        html_content += "</div>"

    html_content += "</body></html>"
    with open(HTML_FILE, "w") as f: f.write(html_content)
    print(f"\n🚀 Comparison Lab Ready! Open '{HTML_FILE}' to see the results.")

if __name__ == "__main__":
    if len(sys.argv) > 1: run_comparison(sys.argv[1])
