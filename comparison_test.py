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

    # --- 1. GLOBAL THRESHOLDING (Steps of 5) ---
    # 6 Variations
    for val in range(225, 255, 5):
        _, t = cv2.threshold(gray, val, 255, cv2.THRESH_BINARY_INV)
        save_v(f"01_threshold_{val}", t)

    # --- 2. CHROMA SHIELD (Lab Color Distance) ---
    # 5 Variations - Higher = more 'color' needed to stay
    l, a, b_chan = cv2.split(lab)
    chroma = cv2.addWeighted(cv2.absdiff(a, 128), 0.5, cv2.absdiff(b_chan, 128), 0.5, 0)
    for c_tol in [4, 8, 12, 16, 20]:
        _, c_mask = cv2.threshold(chroma, c_tol, 255, cv2.THRESH_BINARY)
        save_v(f"02_chroma_shield_tol_{c_tol}", c_mask)

    # --- 3. EDGE-BLOCKED FLOODFILL (The 'Wall' Logic) ---
    # 6 Variations - Testing different 'leak' sensitivities
    edges = cv2.Canny(gray, 20, 100)
    wall = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
    for d in [2, 4, 8, 12, 18, 25]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0, 0, 0] 
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        save_v(f"03_edge_flood_tol_{d}", np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8))

    # --- 4. HYBRID SATURATION + INK (Shadow Protection) ---
    # 5 Variations - Protects colors and dark lines
    sat_mask = cv2.threshold(hsv[:,:,1], 10, 255, cv2.THRESH_BINARY)[1]
    dark_mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)[1]
    shield = cv2.bitwise_or(sat_mask, dark_mask)
    for g_v in [235, 240, 245, 250]:
        g_mask = cv2.threshold(gray, g_v, 255, cv2.THRESH_BINARY_INV)[1]
        save_v(f"04_ink_sat_hybrid_{g_v}", cv2.bitwise_or(g_mask, shield))

    # --- 5. COLOR DISTANCE (From Top-Left Corner) ---
    # 6 Variations - Higher = removes less color
    bg_color = rgb[5, 5].astype(float)
    dist_map = np.sqrt(np.sum((rgb.astype(float) - bg_color)**2, axis=2))
    for d_tol in [10, 20, 30, 40, 50, 60]:
        save_v(f"05_color_dist_{d_tol}", np.where(dist_map > d_tol, 255, 0).astype(np.uint8))

    return image_results

def run_comparison(target_path):
    html_content = """<html><head><style>
        body { font-family: sans-serif; background: #1a1a1a; color: #eee; padding: 20px; }
        .row { display: flex; overflow-x: auto; margin-bottom: 40px; padding: 20px; background: #252525; border-radius: 8px; }
        .img-card { flex: 0 0 280px; margin-right: 20px; text-align: center; background: #333; padding: 10px; border-radius: 4px; }
        .img-card img { width: 100%; height: auto; border: 1px solid #444; margin-top: 10px;
            background-image: linear-gradient(45deg, #333 25%, transparent 25%), linear-gradient(-45deg, #333 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #333 75%), linear-gradient(-45deg, transparent 75%, #333 75%);
            background-size: 16px 16px; background-position: 0 0, 0 8px, 8px -8px, -8px 0px; }
        h2 { color: #ff9f43; margin-top: 30px; border-bottom: 2px solid #ff9f43; display: inline-block; }
    </style></head><body><h1>Background Removal Logic Comparison</h1>"""

    if os.path.isdir(target_path):
        images = [f for f in os.listdir(target_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    else:
        images = [os.path.basename(target_path)]
        target_path = os.path.dirname(target_path)

    for img_name in images:
        full_path = os.path.join(target_path, img_name)
        stem = Path(img_name).stem
        orig_rel = f"{stem}_ORIGINAL.png"
        Image.open(full_path).save(os.path.join(OUTPUT_ROOT, orig_rel))
        
        results = process_logic(full_path, stem)
        html_content += f"<h2>Image: {img_name}</h2><div class='row'>"
        html_content += f"<div class='img-card'><b>ORIGINAL</b><br><img src='{OUTPUT_ROOT}/{orig_rel}'></div>"
        for label, path in results:
            html_content += f"<div class='img-card'><b>{label}</b><br><img src='{OUTPUT_ROOT}/{path}'></div>"
        html_content += "</div>"

    html_content += "</body></html>"
    with open(HTML_FILE, "w") as f: f.write(html_content)
    print(f"\n🏁 Finished! Open '{HTML_FILE}' in your browser.")

if __name__ == "__main__":
    if len(sys.argv) > 1: run_comparison(sys.argv[1])
