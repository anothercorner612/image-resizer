import sys, os, io
import numpy as np
import cv2
from PIL import Image
from pathlib import Path

# Setup output root
OUTPUT_ROOT = "test_results"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

def process_logic(input_path, save_folder):
    """The core 21-version logic engine"""
    pil_img = Image.open(input_path).convert("RGBA")
    original_np = np.array(pil_img)
    rgb = original_np[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape

    def save_v(name, alpha_channel):
        res = original_np.copy()
        res[:, :, 3] = alpha_channel
        Image.fromarray(res).save(os.path.join(save_folder, f"{name}.png"))

    # --- 1-10: DYNAMIC THRESHOLD RANGE (0-255 focus) ---
    # We test every 5 steps in the 'high white' range
    for val in range(200, 250, 5):
        _, t = cv2.threshold(gray, val, 255, cv2.THRESH_BINARY_INV)
        save_v(f"01_thresh_gray_{val}", t)

    # --- 11-15: SATURATION PROTECTION (Saves White Products) ---
    # This ignores brightness and looks for 'color'
    for s_val in [2, 5, 10, 15, 20]:
        _, s_mask = cv2.threshold(hsv[:,:,1], s_val, 255, cv2.THRESH_BINARY)
        save_v(f"02_sat_protect_{s_val}", s_mask)

    # --- 16-18: ADAPTIVE BLOCKING (Handles shadows/gradients) ---
    for block in [11, 31, 71]:
        t_adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, 2)
        save_v(f"03_adaptive_block_{block}", t_adapt)

    # --- 19-21: FLOODFILL 'MAGIC WAND' (Corner logic) ---
    # Prevents white parts inside the ladder from being deleted
    for diff in [2, 5, 8]:
        f_mask = np.zeros((height + 2, width + 2), np.uint8)
        # Click all 4 corners
        for pt in [(0,0), (width-1, 0), (0, height-1), (width-1, height-1)]:
            cv2.floodFill(rgb.copy(), f_mask, pt, (255,255,255), (diff,)*3, (diff,)*3, 8)
        final_f = np.where(f_mask[1:-1, 1:-1] == 1, 0, 255).astype(np.uint8)
        save_v(f"04_floodfill_diff_{diff}", final_f)

def run_comparison(target_path):
    if os.path.isdir(target_path):
        print(f"📂 Batch Mode: Processing folder {target_path}")
        extensions = ('.jpg', '.jpeg', '.png', '.webp')
        images = [f for f in os.listdir(target_path) if f.lower().endswith(extensions)]
        for img in images:
            img_path = os.path.join(target_path, img)
            save_subfolder = os.path.join(OUTPUT_ROOT, Path(img).stem)
            os.makedirs(save_subfolder, exist_ok=True)
            process_logic(img_path, save_subfolder)
    else:
        print(f"📸 Single Mode: Processing {target_path}")
        save_subfolder = os.path.join(OUTPUT_ROOT, Path(target_path).stem)
        os.makedirs(save_subfolder, exist_ok=True)
        process_logic(target_path, save_subfolder)

    print(f"\n🏁 Finished! Results are in '{OUTPUT_ROOT}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_comparison(sys.argv[1])
    else:
        print("Usage: python comparison_test.py [path_to_image_OR_folder]")
