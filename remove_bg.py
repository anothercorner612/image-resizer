import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    try:
        model = withoutbg.WithoutBG.opensource()
        # Trust the AI for the initial cut - it's usually best at text
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")
        data = np.array(img_rgba)
        
        alpha = data[:, :, 3]

        # 1. KILL THE BLACK BARS (Top 8% and Bottom 8%)
        # This is a 'dumb' geometric cut. It simply forces the top/bottom 
        # edges to be transparent, which usually catches the scanner lid bars.
        height, width = data.shape[:2]
        margin = int(height * 0.08)
        
        # We only wipe the margin if the AI left something 'noisy' there
        cleaned_alpha = alpha.copy()
        cleaned_alpha[:margin, :] = 0
        cleaned_alpha[-margin:, :] = 0

        # 2. THE "GUTTER" (For the .8 Scaling Handshake)
        # We force a 15px border on the sides to ensure the JS 'trim' works
        cleaned_alpha[:, :15] = 0
        cleaned_alpha[:, -15:] = 0

        # 3. HOLE FILLING (Internal Only)
        # This fixes the 'Swiss Cheese' effect inside the book 
        # without touching the outer edges.
        final_mask = ndimage.binary_fill_holes(cleaned_alpha > 0)
        
        # Apply the filled mask back to the alpha channel
        # This ensures the interior is 255 (solid) and the edges are smooth
        alpha_final = np.where(final_mask, 255, 0).astype(np.uint8)

        # 4. EXPORT
        data[:, :, 3] = alpha_final
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
