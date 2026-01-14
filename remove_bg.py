import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
import cv2 
import withoutbg

def remove_background(input_path, output_path):
    try:
        # 1. LOAD & PREP
        pil_img = Image.open(input_path).convert("RGBA")
        data = np.array(pil_img)
        h, w = data.shape[:2]

        # 2. THE AI BRAIN (withoutbg)
        # Identifies the product based on learned patterns
        model = withoutbg.WithoutBG.opensource()
        ai_result = model.remove_background(input_path)
        ai_alpha = np.array(ai_result.convert("RGBA"))[:, :, 3]

        # 3. THE TEXTURE BRAIN (Saliency)
        # Identifies the product based on contrast and texture (great for white covers)
        saliency = cv2.saliency.StaticSaliencyFineGrained_create()
        success, saliency_map = saliency.computeSaliency(data[:,:,:3])
        saliency_map = (saliency_map * 255).astype("uint8")
        _, thresh = cv2.threshold(saliency_map, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # 4. THE MERGE
        # Combines both sources of truth
        combined_mask = cv2.bitwise_or(ai_alpha, thresh)

        # 5. HOLE FILLING
        # Fixes the 'fuzzy' or transparent spots in the middle of white books
        final_mask = ndimage.binary_fill_holes(combined_mask > 0)
        
        # 6. ISLAND KILLER
        # Removes small background noise or floating artifacts
        label_im, nb_labels = ndimage.label(final_mask)
        if nb_labels > 1:
            sizes = ndimage.sum(final_mask, label_im, range(nb_labels + 1))
            final_mask = (label_im == np.argmax(sizes))

        # 7. EXPORT WITH 5px SAFETY GUTTER
        # Sharp-edged transparency for the JavaScript scaling logic
        alpha_final = (final_mask * 255).astype(np.uint8)
        alpha_final[:5, :] = 0
        alpha_final[-5:, :] = 0
        alpha_final[:, :5] = 0
        alpha_final[:, -5:] = 0

        data[:, :, 3] = alpha_final
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        print(f"Python Error: {e}", file=sys.stderr)
        return 0

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
