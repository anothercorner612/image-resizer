import sys, os
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    try:
        # 1. LOAD IMAGE
        pil_img = Image.open(input_path).convert("RGBA")
        original_data = np.array(pil_img)

        # 2. GET AI MASK
        model = withoutbg.WithoutBG.opensource()
        ai_result = model.remove_background(input_path)
        alpha = np.array(ai_result.convert("RGBA"))[:, :, 3]

        # 3. CLEAN UP ARTIFACTS (The Halo Fix)
        # Morphological opening removes 'noise' around the edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel, iterations=1)

        # 4. INTELLIGENT HOLE FILLING (The Ladder Fix)
        # We only fill holes that are tiny (noise), not large (geometry)
        contours, hierarchy = cv2.findContours(alpha, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        
        if hierarchy is not None:
            for i, h in enumerate(hierarchy[0]):
                # If it's an internal hole (has a parent contour)
                if h[3] != -1:
                    area = cv2.contourArea(contours[i])
                    # Only fill if hole is less than 0.5% of the total image area
                    if area < (alpha.shape[0] * alpha.shape[1] * 0.005):
                        cv2.drawContours(alpha, [contours[i]], -1, 255, -1)

        # 5. SOFTEN EDGES (The Staircase Fix)
        # Subtle blur makes the transition look natural
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

        # 6. APPLY CLEAN ALPHA
        original_data[:, :, 3] = alpha
        
        # 7. ADD 5px SAFETY GUTTER (For Node.js scaling)
        original_data[:5, :, 3] = 0
        original_data[-5:, :, 3] = 0
        original_data[:, :5, 3] = 0
        original_data[:, -5:, 3] = 0

        Image.fromarray(original_data).save(output_path)
        return 0

    except Exception as e:
        print(f"Python Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
