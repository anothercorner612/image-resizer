import sys, os
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from scipy import ndimage
import withoutbg

def apply_pro_contrast(img_cv):
    """
    Creates a 'Stunt Double' image with aggressive contrast to help the AI 
    find edges on white-on-white products.
    """
    # 1. Convert to LAB color space to separate Lightness from Color
    lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # 2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to Lightness
    # This makes subtle texture differences (paper grain) pop out.
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)

    # 3. Merge back and convert to RGB
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    # 4. Gamma Correction (Darken mid-tones to separate off-white from pure white)
    # Gamma < 1.0 makes shadows/mid-tones darker
    gamma = 0.8
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    enhanced = cv2.LUT(enhanced, table)

    return enhanced

def remove_background(input_path, output_path):
    temp_boosted_path = "temp_boosted_for_ai.jpg"
    
    try:
        # 1. LOAD ORIGINAL IMAGE
        # We read it with OpenCV for the heavy math
        original_cv = cv2.imread(input_path)
        
        # 2. CREATE THE "STUNT DOUBLE"
        # This image is ugly/dark/grainy, but the EDGES are clear.
        boosted_cv = apply_pro_contrast(original_cv)
        cv2.imwrite(temp_boosted_path, boosted_cv)

        # 3. RUN AI ON THE STUNT DOUBLE
        # The AI now sees a "Grey Book on White BG" -> Easy detection!
        model = withoutbg.WithoutBG.opensource()
        ai_result = model.remove_background(temp_boosted_path)
        
        # Extract the Alpha channel (The Cutout Shape)
        ai_alpha = np.array(ai_result.convert("RGBA"))[:, :, 3]

        # 4. "SOLIDIFY" THE MASK
        # Since we boosted contrast, we trust the shape more.
        # We simply remove the "fuzz" (anything < 10% opacity becomes 0, else 255)
        # This fixes the "Blurry Text" issue.
        _, solid_mask = cv2.threshold(ai_alpha, 10, 255, cv2.THRESH_BINARY)

        # 5. HOLE FILLING (The "Swiss Cheese" Fix)
        # Protects the center of the book from being transparent
        filled_mask = ndimage.binary_fill_holes(solid_mask > 0)
        
        # 6. ISLAND KILLER
        # Removes floating dust spots
        label_im, nb_labels = ndimage.label(filled_mask)
        if nb_labels > 1:
            sizes = ndimage.sum(filled_mask, label_im, range(nb_labels + 1))
            filled_mask = (label_im == np.argmax(sizes))

        # 7. APPLY MASK TO ORIGINAL
        # We create the final output using the ORIGINAL pixels + the BOOSTED mask
        pil_original = Image.open(input_path).convert("RGBA")
        data = np.array(pil_original)
        
        # Apply the 5px safety gutter for JS scaling
        alpha_final = (filled_mask * 255).astype(np.uint8)
        alpha_final[:5, :] = 0
        alpha_final[-5:, :] = 0
        alpha_final[:, :5] = 0
        alpha_final[:, -5:] = 0

        data[:, :, 3] = alpha_final
        Image.fromarray(data).save(output_path)
        
        # Cleanup
        if os.path.exists(temp_boosted_path):
            os.remove(temp_boosted_path)
            
        return 0

    except Exception as e:
        print(f"Python Error: {e}", file=sys.stderr)
        if os.path.exists(temp_boosted_path):
            os.remove(temp_boosted_path)
        return 0

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
