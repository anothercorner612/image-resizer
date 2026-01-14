import sys, os, io
import numpy as np
import cv2
from PIL import Image, ImageCms
from scipy import ndimage
import withoutbg

# Ensure output directory exists
os.makedirs("test_results", exist_ok=True)

def save_result(name, data, output_path):
    print(f"✅ Generated: {name}")
    Image.fromarray(data).save(os.path.join("test_results", f"{name}.png"))

def run_comparison(input_path):
    print(f"🚀 Running 6-way comparison for: {input_path}")
    model = withoutbg.WithoutBG.opensource()
    
    # Load base images
    pil_img = Image.open(input_path).convert("RGBA")
    original_np = np.array(pil_img)
    gray_guide = cv2.cvtColor(original_np[:,:,:3], cv2.COLOR_RGBA2GRAY)
    
    # Get base AI Alpha once to save time
    base_ai_result = model.remove_background(input_path)
    base_alpha = np.array(base_ai_result.convert("RGBA"))[:, :, 3]

    # --- OPTION 1: Matting & Color (Guided Filter) ---
    # Good for: Smooth edges, removing jaggies
    refined_alpha = cv2.ximgproc.guidedFilter(gray_guide, base_alpha, 10, 1e-6)
    opt1 = original_np.copy()
    opt1[:, :, 3] = refined_alpha
    save_result("01_matting_filter", opt1, input_path)

    # --- OPTION 2: Geometry Guardian (Area-Based) ---
    # Good for: Ladders and chairs (prevents filling large gaps)
    opt2_alpha = base_alpha.copy()
    contours, hier = cv2.findContours(opt2_alpha, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    img_area = opt2_alpha.shape[0] * opt2_alpha.shape[1]
    if hier is not None:
        for i, h in enumerate(hier[0]):
            if h[3] != -1: # Internal hole
                if cv2.contourArea(contours[i]) < (img_area * 0.002):
                    cv2.drawContours(opt2_alpha, [contours[i]], -1, 255, -1)
    opt2 = original_np.copy()
    opt2[:, :, 3] = opt2_alpha
    save_result("02_geometry_guardian", opt2, input_path)

    # --- OPTION 3: ICC Profile Master ---
    # Good for: Fixing 'Sunwashed' colors from Adobe RGB
    opt3_img = Image.open(input_path)
    if opt3_img.info.get('icc_profile'):
        f = io.BytesIO(opt3_img.info.get('icc_profile'))
        opt3_img = ImageCms.profileToProfile(opt3_img, f, ImageCms.createProfile("sRGB"))
    opt3_res = model.remove_background(opt3_img)
    save_result("03_color_profile_fix", np.array(opt3_res.convert("RGBA")), input_path)

    # --- OPTION 4: Bilateral Edge Filter ---
    # Good for: Removing 'Halos' and background noise
    smoothed_rgb = cv2.bilateralFilter(original_np[:,:,:3], 9, 75, 75)
    opt4_res = model.remove_background(Image.fromarray(smoothed_rgb))
    save_result("04_bilateral_denoise", np.array(opt4_res.convert("RGBA")), input_path)

    # --- OPTION 5: Watershed Seed ---
    # Good for: Finding lost tops of white books
    markers = np.zeros(base_alpha.shape, dtype=np.int32)
    markers[base_alpha < 50] = 1
    markers[base_alpha > 200] = 2
    cv2.watershed(original_np[:,:,:3], markers)
    opt5_alpha = np.where(markers == 2, 255, 0).astype(np.uint8)
    opt5 = original_np.copy()
    opt5[:, :, 3] = opt5_alpha
    save_result("05_watershed_boundary", opt5, input_path)

    # --- OPTION 6: Gamma-Corrected Alpha ---
    # Good for: Fixing 'Sunwashed' look by thickening the mask
    opt6_alpha = (np.power(base_alpha.astype(float)/255.0, 0.5) * 255).astype(np.uint8)
    opt6 = original_np.copy()
    opt6[:, :, 3] = opt6_alpha
    save_result("06_gamma_thick_mask", opt6, input_path)

    print("\n🏁 DONE! Check the 'test_results' folder to compare.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_comparison(sys.argv[1])
    else:
        print("Usage: python comparison_test.py your_image.jpg")
