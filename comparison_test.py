import sys, os, io
import numpy as np
import cv2
from PIL import Image
from pathlib import Path

OUTPUT_ROOT = "test_results"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

def process_logic(input_path, save_folder):
    pil_img = Image.open(input_path).convert("RGBA")
    original_np = np.array(pil_img)
    rgb = original_np[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    height, width = gray.shape

    def save_v(name, alpha_channel):
        res = original_np.copy()
        res[:, :, 3] = alpha_channel
        Image.fromarray(res).save(os.path.join(save_folder, f"{name}.png"))

    # --- 1-5: REFINED THRESHOLDS (Tight Steps) ---
    for val in [230, 238, 242, 246, 250]:
        _, t = cv2.threshold(gray, val, 255, cv2.THRESH_BINARY_INV)
        save_v(f"01_thresh_{val}", t)

    # --- 6-9: THE "CHROMA" FILTERS (Ignoring Lightness) ---
    # These focus ONLY on color. Great for the ladder illustration.
    l, a, b_chan = cv2.split(lab)
    _, a_t = cv2.threshold(cv2.absdiff(a, 128), 10, 255, cv2.THRESH_BINARY) # Color vs Neutral
    _, b_t = cv2.threshold(cv2.absdiff(b_chan, 128), 10, 255, cv2.THRESH_BINARY)
    chroma_mask = cv2.bitwise_or(a_t, b_t)
    save_v("02_chroma_presence_mask", chroma_mask)

    # --- 10-13: FLOODFILL WITH GRADIENT BARRIERS ---
    # This prevents the 'leak' by creating a thin wall of edges
    edges = cv2.Canny(gray, 30, 100)
    dilated_edges = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
    
    for d in [4, 8, 12]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        # We fill an image that has the edges 'burned' into it
        temp_rgb = rgb.copy()
        temp_rgb[dilated_edges == 255] = [0, 0, 0] 
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        save_v(f"03_edge_blocked_flood_{d}", np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8))

    # --- 14-16: HYBRID: SATURATION + GRAY THRESHOLD ---
    # Only removes pixels if they are BOTH bright AND colorless
    sat_mask = cv2.threshold(hsv[:,:,1], 8, 255, cv2.THRESH_BINARY)[1]
    for g_v in [240, 248]:
        gray_mask = cv2.threshold(gray, g_v, 255, cv2.THRESH_BINARY_INV)[1]
        hybrid = cv2.bitwise_or(gray_mask, sat_mask)
        save_v(f"04_hybrid_sat_gray_{g_v}", hybrid)

    # --- 17-19: MORPHOLOGICAL "HOLE FILLING" ---
    # Good for ladders where the AI misses the middle of a rung
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    _, base_t = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    closed = cv2.morphologyEx(base_t, cv2.MORPH_CLOSE, kernel)
    save_v("05_morph_closed_5x5", closed)

    # --- 20-22: MULTI-LEVEL SALIENCY ---
    # Tries to find 'objects' based on contrast and color patterns
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    success, s_map = saliency.computeSaliency(rgb)
    s_map = (s_map * 255).astype("uint8")
    save_v("06_saliency_raw", s_map)
    _, s_t = cv2.threshold(s_map, 10, 255, cv2.THRESH_BINARY)
    save_v("06_saliency_thresh", s_t)

    # --- 23-25: THE "CORNER-COLOR" REMOVER ---
    # Samples the top-left pixel color and removes everything similar to it
    bg_color = rgb[5, 5].astype(float)
    diff = np.sqrt(np.sum((rgb.astype(float) - bg_color)**2, axis=2))
    for tol in [15, 30, 45]:
        mask = np.where(diff > tol, 255, 0).astype(np.uint8)
        save_v(f"07_color_distance_tol_{tol}", mask)

def run_comparison(target_path):
    if os.path.isdir(target_path):
        images = [f for f in os.listdir(target_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        for img in images:
            save_subfolder = os.path.join(OUTPUT_ROOT, Path(img).stem)
            os.makedirs(save_subfolder, exist_ok=True)
            process_logic(os.path.join(target_path, img), save_subfolder)
    else:
        save_subfolder = os.path.join(OUTPUT_ROOT, Path(target_path).stem)
        os.makedirs(save_subfolder, exist_ok=True)
        process_logic(target_path, save_subfolder)
    print(f"\n🏁 Finished! Results in '{OUTPUT_ROOT}'")

if __name__ == "__main__":
    if len(sys.argv) > 1: run_comparison(sys.argv[1])
