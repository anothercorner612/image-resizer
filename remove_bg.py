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
        # Use float for precision math
        r, g, b = data[:,:,0].astype(float), data[:,:,1].astype(float), data[:,:,2].astype(float)

        # 1. SCANNER-WHITE REJECTION (Strict)
        is_not_white = (r < 251) | (g < 251) | (b < 251)
        
        # 2. THE SOLIDIFIER (Fixes blur/fuzziness on white covers)
        # If it's not scanner-white AND the AI thinks it's likely foreground,
        # we force it to be 100% solid (255). This removes the 'haze'.
        mask = (alpha > 80) | is_not_white
        mask = ndimage.binary_fill_holes(mask)

        # 3. THE "ISLAND KILLER"
        label_im, nb_labels = ndimage.label(mask)
        if nb_labels > 1:
            sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
            mask = (label_im == np.argmax(sizes))

        # 4. EDGE SHARPENING
        # Instead of 'Closing' (which blurs), we use a tiny bit of 'Erosion' 
        # followed by 'Dilation' to snap the edges to the text.
        mask = ndimage.binary_opening(mask, structure=np.ones((2,2)))

        # 5. CONVERT TO HARD ALPHA (No semi-transparency)
        final_alpha = (mask * 255).astype(np.uint8)

        # 6. THE GUTTER (For scaling)
        final_alpha[:15, :] = 0
        final_alpha[-15:, :] = 0
        final_alpha[:, :15] = 0
        final_alpha[:, -15:] = 0

        # 7. EXPORT
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
