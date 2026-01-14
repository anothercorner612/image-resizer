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

        # 1. ROBUST MASK (Reject scanner-white and keep AI results)
        is_not_white = (r < 252) | (g < 252) | (b < 252)
        mask = (alpha > 100) | is_not_white

        # 2. FILL INTERNAL GAPS (Protects envelopes)
        mask = ndimage.binary_fill_holes(mask)

        # 3. ISLAND KILLER (Remove any stray pixels not touching the book)
        label_im, nb_labels = ndimage.label(mask)
        if nb_labels > 1:
            sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
            mask = (label_im == np.argmax(sizes))

        # 4. HARD BINARY CLEANUP
        # We convert the mask to a hard 0 or 255. No semi-transparency in background.
        cleaned_alpha = (mask * 255).astype(np.uint8)

        # 5. THE "GUTTER"
        # Force the absolute edges to 0 so JS 'trim' has a guaranteed starting point
        h, w = cleaned_alpha.shape
        cleaned_alpha[:15, :] = 0
        cleaned_alpha[-15:, :] = 0
        cleaned_alpha[:, :15] = 0
        cleaned_alpha[:, -15:] = 0

        # 6. EXPORT
        data[:, :, 3] = cleaned_alpha
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
