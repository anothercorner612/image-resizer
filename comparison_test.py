import sys, os, io
import numpy as np
import cv2
from PIL import Image, ImageCms
from scipy import ndimage
import withoutbg

# Ensure output directory exists
os.makedirs("test_results", exist_ok=True)

def save_result(name, data):
    print(f"✅ Generated: {name}")
    Image.fromarray(data).save(os.path.join("test_results", f"{name}.png"))

def run_comparison(input_path):
    print(f"🚀 Running FOCUS-CROP comparison for: {input_path}")
    model = withoutbg.WithoutBG.opensource()
    
    # 1. LOAD ORIGINAL
    pil_img = Image.open(input_path).convert("RGBA")
    width, height = pil_img.size
    original_np = np.array(pil_img)

    # 2. APPLY FOCUS CROP (Remove outer 15% to ignore peripheral text/icons)
    # Adjust these decimals (0.15) if the product itself is being cut off
    left = int(width * 0.15)
    top = int(height * 0.15)
    right = int(width * 0.85)
    bottom = int(height * 0.85)
    focused_img = pil_img.crop((left, top, right, bottom))
    
    # 3. GET AI MASK FROM CROPPED VERSION
    print("🧠 Analyzing centered product...")
    base_ai_result = model.remove_background(focused_img)
    cropped_alpha = np.array(base_ai_result.convert("RGBA"))[:, :, 3]

    # 4. RE-EXPAND MASK TO FULL SIZE
    # Start with a pure black (transparent) canvas
    full_alpha = np.zeros((height, width), dtype=np.uint8)
    # Place the "clean" cropped mask back into the center of the full frame
    full_alpha[top:bottom, left:right] = cropped_alpha
    
    # Use this cleaned mask as the foundation for all options
    base_alpha = full_alpha
    gray_guide = cv2.cvtColor(original_np[:,:,:3], cv2.COLOR_RGBA2GRAY)

    # --- OPTION 1: Matting (Guided Filter) ---
    if hasattr(cv2, 'ximgproc'):
        refined_alpha = cv2.ximgproc.guidedFilter(gray_guide, base_alpha, 10, 1e-6)
        opt1 = original_np.copy()
        opt1[:, :, 3] = refined_alpha
        save_result("01_matting_filter", opt1)
    else:
        print("⚠️ Skipping Option 1: opencv-contrib-python not fully recognized.")

    # --- OPTION 2: Geometry Guardian (Area-Based Hole Filling) ---
    opt2_alpha = base_alpha.copy()
    contours, hier = cv2.findContours(opt2_alpha, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    img_area = width * height
    if hier is not None:
        for i, h in enumerate(hier[0]):
            if h[3] != -1: # It's a hole
                if cv2.contourArea(contours[i]) < (img_area * 0.002):
                    cv2.drawContours(opt2_alpha, [contours[i]], -1, 255, -1)
    opt2 = original_np.copy()
    opt2[:, :, 3] = opt2_alpha
    save_result("02_geometry_guardian", opt2)

    # --- OPTION 3: ICC Profile Master (Color Pop) ---
    opt3_img = Image.open(input_path)
    if opt3_img.info.get('icc_profile'):
        f = io.BytesIO(opt3_img.info.get('icc_profile'))
        opt3_img = ImageCms.profileToProfile(opt3_img, f, ImageCms.createProfile("sRGB"))
    opt3_res = model.remove_background(opt3_img)
    save_result("03_color_profile_fix", np.array(opt3_res.convert("RGBA")))

    # --- OPTION 4: Bilateral Edge Filter (Halo Removal) ---
    smoothed_rgb = cv2.bilateralFilter(original_np[:,:,:3], 9, 75, 75)
    # Apply mask from cropped logic to the smoothed RGB
    opt4 = original_np.copy()
    opt4[:,:,:3] = smoothed_rgb
    opt4[:, :, 3] = base_alpha
    save_result("04_bilateral_denoise", opt4)

    # --- OPTION 5: Watershed Seed (Boundary Search) ---
    markers = np.zeros(base_alpha.shape, dtype=np.int32)
    markers[base_alpha < 50] = 1 # Sure background
    markers[base_alpha > 200] = 2 # Sure product
    cv2.watershed(original_np[:,:,:3], markers)
    opt5_alpha = np.where(markers == 2, 255, 0).astype(np.uint8)
    opt5 = original_np.copy()
    opt5[:, :, 3] = opt5_alpha
    save_result("05_watershed_boundary", opt5)

    # --- OPTION 6: Gamma-Corrected Alpha (Opacity Fix) ---
    opt6_alpha = (np.power(base_alpha.astype(float)/255.0, 0.5) * 255).astype(np.uint8)
    opt6 = original_np.copy()
    opt6[:, :, 3] = opt6_alpha
    save_result("06_gamma_thick_mask", opt6)

    print("\n🏁 DONE! Check the 'test_results' folder.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_comparison(sys.argv[1])
    else:
        print("Usage: python comparison_test.py path/to/image.webp")
