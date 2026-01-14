import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
import cv2 
import withoutbg

def remove_background(input_path, output_path):
    try:
        # 1. LOAD IMAGE
        pil_img = Image.open(input_path).convert("RGBA")
        data = np.array(pil_img)
        gray = cv2.cvtColor(data, cv2.COLOR_RGBA2GRAY)

        # 2. AI PASS (The Brain)
        model = withoutbg.WithoutBG.opensource()
        ai_result = model.remove_background(input_path)
        ai_alpha = np.array(ai_result.convert("RGBA"))[:, :, 3]

        # 3. CANNY PASS (The Edges)
        # Finds high-contrast edges (like text and card boundaries)
        edges = cv2.Canny(gray, 30, 100)
        
        # Dilate the edges to connect them into a solid block
        kernel = np.ones((15, 15), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Fill the holes inside the edges to create a solid "object" mask
        filled_edges = ndimage.binary_fill_holes(dilated_edges > 0)

        # 4. SMART MERGE
        # Keep pixels if AI says 'it's a book' OR Canny found 'edges of a book'
        combined_mask = cv2.bitwise_or(ai_alpha, (filled_edges * 255).astype(np.uint8))

        # 5. HOLE FILLING & ISLAND CLEANUP
        # Ensures the center of the white cover is 100% solid
        final_mask = ndimage.binary_fill_holes(combined_mask > 0)
        
        label_im, nb_labels = ndimage.label(final_mask)
        if nb_labels > 1:
            sizes = ndimage.sum(final_mask, label_im, range(nb_labels + 1))
            final_mask = (label_im == np.argmax(sizes))

        # 6. EXPORT WITH 5px GUTTER
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
