import sys
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    try:
        if not os.path.exists(input_path):
            return 1

        # Initialize model
        model = withoutbg.WithoutBG.opensource()
        
        # Get initial AI Alpha Mask
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")
        data = np.array(img_rgba)
        
        rgb = data[:, :, 0:3]
        alpha = data[:, :, 3]

        # 1. BRIGHTNESS & COLOR ANALYSIS
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
        # Standard luminance formula
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        saturation = np.max(rgb, axis=2) - np.min(rgb, axis=2)
        
        # 2. THE RECOVERY MASK
        # We accept pixels that are: 
        # - Identified by AI (alpha > 5)
        # - NOT pure white background (luminance < 235)
        # - Or have vivid colors (saturation > 20)
        combined_mask = (alpha > 5) | (luminance < 235) | (saturation > 20)

        # 3. VERTICAL ANCHOR (Fixes "Flat Tops" on white books)
        # We scan each column. If we find product at the bottom but a gap at the top,
        # we bridge the top gap to allow 'binary_fill_holes' to work properly.
        for col in range(combined_mask.shape[1]):
            column = combined_mask[:, col]
            if np.any(column):
                first_pixel = np.where(column)[0][0]
                # If the product starts further down than expected, it's likely 
                # a 'beheaded' white edge. We anchor the top 20 pixels.
                if first_pixel > 2 and first_pixel < 100:
                    combined_mask[0:first_pixel, col] = True

        # 4. ARTIFACT CLEANUP (Removes scanning bars/islands)
        label_im, nb_labels = ndimage.label(combined_mask)
        if nb_labels > 1:
            sizes = ndimage.sum(combined_mask, label_im, range(nb_labels + 1))
            mask_size = sizes < (sizes.max() * 0.1)
            remove_pixel = mask_size[label_im]
            combined_mask[remove_pixel] = 0

        # 5. STRUCTURAL BRIDGE & HOLE FILLING
        # Using a taller structure (12x5) to help close vertical gaps in book covers
        struct = np.ones((12, 5)) 
        mask = ndimage.binary_closing(combined_mask, structure=struct, iterations=2)
        mask = ndimage.binary_fill_holes(mask)

        # 6. RECONSTRUCT ALPHA
        data[:, :, 3] = (mask * 255).astype(np.uint8)
        final_image = Image.fromarray(data)
        
        # Subtle Gaussian blur to smooth the anti-aliased edges
        final_image = final_image.filter(ImageFilter.GaussianBlur(radius=0.1))

        final_image.save(output_path)
        return 0

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
