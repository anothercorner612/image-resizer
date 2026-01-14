import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    try:
        model = withoutbg.WithoutBG.opensource()
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")
        data = np.array(img_rgba)
        
        alpha = data[:, :, 3]
        r, g, b = data[:,:,0].astype(float), data[:,:,1].astype(float), data[:,:,2].astype(float)

        # 1. SCANNER-WHITE REJECTION
        # Anything very close to pure white is forced to transparent
        is_not_white = (r < 252) | (g < 252) | (b < 252)
        
        # 2. CREATE SOLID MASK
        # We combine AI mask with our color-check and fill holes (fixes envelopes)
        mask = (alpha > 100) | is_not_white
        mask = ndimage.binary_fill_holes(mask)

        # 3. THE "ISLAND KILLER" (Crucial for Scaling)
        # Finds the book and deletes any stray shadows or black bars at the edges
        label_im, nb_labels = ndimage.label(mask)
        if nb_labels > 1:
            sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
            mask = (label_im == np.argmax(sizes))

        # 4. SMOOTH THE EDGES
        mask = ndimage.binary_closing(mask, structure=np.ones((3,3)))

        # 5. THE "GUTTER" (The .8 Scaling Handshake)
        # We force a 15px border of 100% transparency. 
        # This ensures Sharp's .trim() always has a clean edge to start from.
        h, w = mask.shape
        final_alpha = (mask * 255).astype(np.uint8)
        final_alpha[:15, :] = 0
        final_alpha[-15:, :] = 0
        final_alpha[:, :15] = 0
        final_alpha[:, -15:] = 0

        # 6. EXPORT
        data[:, :, 3] = final_alpha
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        print(f"Python Error: {e}", file=sys.stderr)
        if 'result_image' in locals():
            result_image.save(output_path)
        return 0

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
