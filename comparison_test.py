import sys, os, io
import numpy as np
import cv2
from PIL import Image
from pathlib import Path

# --- CONFIGURATION ---
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

    # --- SHARED ASSETS ---
    edges = cv2.Canny(gray, 20, 100)
    wall = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)

    # --- 1. GEOMETRIC FILL (Fixes hollow centers without losing edge accuracy) ---
    # This finds the 'Outer Shell' and fills everything inside it.
    for d in [4, 12, 25]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0,0,0]
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        mask = np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        
        # Geometry logic: Only the outermost boundary defines the product
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        geo_mask = np.zeros_like(mask)
        cv2.drawContours(geo_mask, contours, -1, 255, thickness=cv2.FILLED)
        save_v(f"01_Geo_Fill_Tol_{d}", geo_mask)

    # --- 2. LAB B-CHANNEL DISTANCE (The Yellow-Background Specialist) ---
    # This is purely color-based, ignoring how bright or dark the rungs are.
    l, a_ch, b_ch = cv2.split(lab)
    bg_b_val = b_ch[5,5] # Sample background yellow/blue value
    diff_b = cv2.absdiff(b_ch, bg_b_val)
    for t_val in [12, 24, 36]:
        _, b_mask = cv2.threshold(diff_b, t_val, 255, cv2.THRESH_BINARY)
        save_v(f"02_Lab_Yellow_Killer_{t_val}", b_mask)

    # --- 3. HEALED STRICT (Strict edges + Color-Based recovery) ---
    # This uses your preferred Strict logic but 'protects' colorful pixels.
    sat_shield = cv2.threshold(hsv[:,:,1], 10, 255, cv2.THRESH_BINARY)[1]
    for d in [4, 15, 30]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0,0,0]
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        strict_mask = np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        
        # Combine the strict cutout with the colorful product parts
        healed_mask = cv2.bitwise_or(strict_mask, sat_shield)
        save_v(f"03_Healed_Strict_Tol_{d}", healed_mask)

    # --- 4. MORPHOLOGICAL CLOSED (The 'Soap-Bubble' Edges) ---
    # Smoothes out noise and snaps small holes shut.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    for d in [5, 15, 25]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0,0,0]
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        raw_mask = np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        
        closed_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel)
        save_v(f"04_Morph_Closed_Tol_{d}", closed_mask)

    return image_results

def run_comparison(target_path):
    html_content = """<html><head><style>
        body { font-family: sans-serif; background: #050505; color: #fff; padding: 20px; }
        .row { display: flex; overflow-x: auto; margin-bottom: 50px; padding: 25px; background: #111; border-radius: 15px; border: 1px solid #222; }
        .img-card { flex: 0 0 320px; margin-right: 25px; text-align: center; background: #1a1a1a; padding: 15px; border-radius: 10px; }
        .img-card b { display: block; margin-bottom: 10px; color: #00d2ff; text-transform: uppercase; font-size: 0.75em; letter-spacing: 1px; }
        .img-card img { width: 100%; height: auto; border: 1px solid #333; 
            background-image: linear-gradient(45deg, #0a0a0a 25%, transparent 25%), linear-gradient(-45deg, #0a0a0a 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #0a0a0a 75%), linear-gradient(-45deg, transparent 75%, #0a0a0a 75%);
            background-size: 16px 16px; background-position: 0 0, 0 8px, 8px -8px, -8px 0px; }
        h2 { color: #f39c12; margin-left: 10px; border-left: 4px solid #f39c12; padding-left: 15px; }
        .orig-label { color: #ff4757 !important; }
    </style></head><body><h1>Final 12: Structure & Color Reconstruction</h1>"""

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
        html_content += f"<div class='img-card'><b class='orig-label'>ORIGINAL</b><img src='{OUTPUT_ROOT}/{orig_rel}'></div>"
        for label, path in results:
            html_content += f"<div class='img-card'><b>{label}</b><img src='{OUTPUT_ROOT}/{path}'></div>"
        html_content += "</div>"

    html_content += "</body></html>"
    with open(HTML_FILE, "w") as f:
        f.write(html_content)
    print(f"\n🚀 Final Lab Ready! Open '{HTML_FILE}'")

if __name__ == "__main__":
    if len(sys.argv) > 1: run_comparison(sys.argv[1])
