import sys, os, io
import numpy as np
import cv2
from PIL import Image, ImageCms

# Ensure output directory exists
os.makedirs("test_results", exist_ok=True)

def save_result(name, data):
    print(f"✅ Generated: {name}")
    Image.fromarray(data).save(os.path.join("test_results", f"{name}.png"))

def run_comparison(input_path):
    print(f"🚀 Running EDGE-BASED comparison for: {input_path}")
    
    # 1. LOAD ORIGINAL
    pil_img = Image.open(input_path).convert("RGBA")
    original_np = np.array(pil_img)
    rgb = original_np[:, :, :3]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    # --- OPTION 1: Sharp Edge Detection (The 'Ladder' Fix) ---
    # Finds the sharp outlines of the ladder
    edges = cv2.Canny(gray, 100, 200)
    kernel = np.ones((3,3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    
    opt1 = original_np.copy()
    opt1[:, :, 3] = dilated
    save_result("01_canny_edges", opt1)

    # --- OPTION 2: Thickened Outlines ---
    # Better for thin rungs that the AI usually deletes
    thick_kernel = np.ones((5,5), np.uint8)
    thick_edges = cv2.dilate(edges, thick_kernel, iterations=2)
    opt2 = original_np.copy()
    opt2[:, :, 3] = thick_edges
    save_result("02_thick_outlines", opt2)

    # --- OPTION 3: Threshold Masking ---
    # Good for high-contrast illustrations
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    opt3 = original_np.copy()
    opt3[:, :, 3] = thresh
    save_result("03_threshold_inverse", opt3)

    # --- OPTION 4: Adaptive Mean Thresholding ---
    # Handles shadows better than standard thresholding
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    opt4 = original_np.copy()
    opt4[:, :, 3] = adaptive
    save_result("04_adaptive_edges", opt4)

    # --- OPTION 5: Saliency Map (What 'Stands Out') ---
    saliency = cv2.saliency.StaticSaliencyFineGrained_create()
    success, saliency_map = saliency.computeSaliency(rgb)
    saliency_map = (saliency_map * 255).astype("uint8")
    _, sal_thresh = cv2.threshold(saliency_map, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    opt5 = original_np.copy()
    opt5[:, :, 3] = sal_thresh
    save_result("05_saliency_map", opt5)

    # --- OPTION 6: GrabCut (Manual Seed) ---
    # We tell the computer the center 80% is definitely the product
    mask = np.zeros(rgb.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rect = (int(rgb.shape[1]*0.1), int(rgb.shape[0]*0.1), int(rgb.shape[1]*0.8), int(rgb.shape[0]*0.8))
    cv2.grabCut(rgb, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
    
    opt6 = original_np.copy()
    opt6[:, :, 3] = mask2 * 255
    save_result("06_grabcut_center", opt6)

    print("\n🏁 DONE! Check the 'test_results' folder.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_comparison(sys.argv[1])
    else:
        print("Usage: python comparison_test.py path/to/image.webp")
