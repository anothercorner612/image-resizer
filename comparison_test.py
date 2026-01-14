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

    # --- 1-5: REFINED THRESHOLDS ---
    for val in [230, 238, 242, 246, 250]:
        _, t = cv2.threshold(gray, val, 255, cv2.THRESH_BINARY_INV)
        save_v(f"01_thresh_{val}", t)

    # --- 6-9: CHROMA/COLOR FILTERS ---
    l, a, b_chan = cv2.split(lab)
    _, a_t = cv2.threshold(cv2.absdiff(a, 128), 8, 255, cv2.THRESH_BINARY)
    _, b_t = cv2.threshold(cv2.absdiff(b_chan, 128), 8, 255, cv2.THRESH_BINARY)
    chroma_mask = cv2.bitwise_or(a_t, b_t)
    save_v("02_chroma_presence_mask", chroma_mask)

    # --- 10-13: EDGE-BLOCK FLOODFILL ---
    edges = cv2.Canny(gray, 30, 100)
    dilated_edges = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
    for d in [5, 12]:
        f_m = np.zeros((height + 2, width + 2), np.uint8)
        temp_rgb = rgb.copy()
        temp_rgb[dilated_edges == 255] = [0, 0, 0] 
        cv2.floodFill(temp_rgb, f_m, (0,0), (255,255,255), (d,)*3, (d,)*3, 8)
        save_v(f"03_edge_blocked_flood_{d}", np.where(f_m[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8))

    # --- 14-16: SAT-GRAY HYBRID ---
    sat_mask = cv2.threshold(hsv[:,:,1], 6, 255, cv2.THRESH_BINARY)[1]
    for g_v in [235, 245]:
        gray_mask = cv2.threshold(gray, g_v, 255, cv2.THRESH_BINARY_INV)[1]
        save_v(f"04_hybrid_sat_gray_{g_v}", cv2.bitwise_or(gray_mask, sat_mask))

    # --- 17-18: MORPHOLOGY ---
    kernel = np.ones((5,5), np.uint8)
    _, base_t = cv2.threshold(gray, 242, 255, cv2.THRESH_BINARY_INV)
    save_v("05_morph_closed", cv2.morphologyEx(base_t, cv2.MORPH_CLOSE, kernel))

    # --- 19-21: COLOR DISTANCE ---
    bg_color = rgb[5, 5].astype(float)
    diff = np.sqrt(np.sum((rgb.astype(float) - bg_color)**2, axis=2))
    for tol in [20, 40]:
        save_v(f"06_color_dist_tol_{tol}", np.where(diff > tol, 255, 0).astype(np.uint8))

    # --- 22-23: SOBEL EDGE HYBRID (New Replace for Saliency) ---
    # Good for finding the 'texture' of the ladder rungs
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    sobel_combined = cv2.magnitude(sobelx, sobely)
    sobel_norm = cv2.normalize(sobel_combined, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, sobel_t = cv2.threshold(sobel_norm, 20, 255, cv2.THRESH_BINARY)
    save_v("07_sobel_texture_mask", sobel_t)

    # --- 24-25: THE "SHADOW PROTECTOR" ---
    # Targets darker 'ink' lines to prevent them from becoming transparent
    _, shadow_mask = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    final_shadow = cv2.bitwise_or(base_t, shadow_mask)
    save_v("08_shadow_ink_protection", final_shadow)

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
    else: print("Usage: python comparison_test.py [path]")
