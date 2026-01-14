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

    # --- 1. THE "COLOR SENSOR" HYBRIDS (Great for the Ladder) ---
    # Looks for any color that ISN'T the background corner color
    bg_color_hsv = hsv[5, 5].astype(int)
    lower_bg = np.array([max(0, bg_color_hsv[0]-10), 20, 20])
    upper_bg = np.array([min(180, bg_color_hsv[0]+10), 255, 255])
    bg_mask = cv2.inRange(hsv, lower_bg, upper_bg)
    save_v("hsv_bg_dist", cv2.bitwise_not(bg_mask))

    # --- 2. THE "LADDER SHIELD" (Lab Color space) ---
    # Separates based on A/B channels (Pink/Green and Blue/Yellow)
    l, a, b_chan = cv2.split(lab)
    a_dist = cv2.absdiff(a, 128)
    b_dist = cv2.absdiff(b_chan, 128)
    chroma = cv2.addWeighted(a_dist, 0.5, b_dist, 0.5, 0)
    _, chroma_t = cv2.threshold(chroma, 10, 255, cv2.THRESH_BINARY)
    save_v("lab_chroma_shield", chroma_t)

    # --- 3. RECURSIVE EDGE-BLOCK (Stronger version of your favorite) ---
    edges = cv2.Canny(gray, 20, 80)
    wall = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=2)
    for d in [6, 15]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[wall == 255] = [0, 0, 0] # Burn edges to stop leaks
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        save_v(f"wall_flood_tol_{d}", np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8))

    # --- 4. THE "VAN PROTECTOR" (Sat + Dark Hybrid) ---
    # Protects pixels that are either Dark (ink) or Colorful (van body)
    sat_mask = cv2.threshold(hsv[:,:,1], 10, 255, cv2.THRESH_BINARY)[1]
    dark_mask = cv2.threshold(gray, 70, 255, cv2.THRESH_BINARY_INV)[1]
    shield = cv2.bitwise_or(sat_mask, dark_mask)
    for g_v in [240, 245]:
        g_mask = cv2.threshold(gray, g_v, 255, cv2.THRESH_BINARY_INV)[1]
        save_v(f"ink_sat_hybrid_{g_v}", cv2.bitwise_or(g_mask, shield))

    # --- 5. CENTER-WEIGHTED GRABCUT (Computer Vision approach) ---
    mask = np.zeros(rgb.shape[:2], np.uint8)
    bgd = np.zeros((1, 65), np.float64); fgd = np.zeros((1, 65), np.float64)
    rect = (10, 10, width-20, height-20)
    try:
        cv2.grabCut(rgb, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        gc_mask = np.where((mask==2)|(mask==0), 0, 255).astype('uint8')
        save_v("grabcut_center", gc_mask)
    except: pass

    # --- 6. MULTI-CHANNEL MAX ---
    # Takes the strongest signal from R, G, and B thresholds
    r, g, b_c = cv2.split(rgb)
    _, rt = cv2.threshold(r, 245, 255, cv2.THRESH_BINARY_INV)
    _, gt = cv2.threshold(g, 245, 255, cv2.THRESH_BINARY_INV)
    _, bt = cv2.threshold(b_c, 245, 255, cv2.THRESH_BINARY_INV)
    save_v("max_channel_threshold", cv2.bitwise_or(rt, cv2.bitwise_or(gt, bt)))

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
        h2 { color: #ff9f43; margin-top: 30px; }
    </style></head><body><h1>Logic Stress-Test Gallery</h1>"""

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
