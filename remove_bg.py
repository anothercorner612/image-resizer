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
        rgb = data[:, :, 0:3]
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]

        # 1. THE CORE MASK (High threshold to avoid shadow-blocks)
        mask = (alpha > 125)

        # 2. THE "GLUE" STEP (Prevents accidental cropping)
        # We temporarily expand the mask to join parts of the book that 
        # might be separated by a thin line of white or text.
        glued_mask = ndimage.binary_dilation(mask, iterations=5)

        # 3. COMPONENT ANALYSIS (Island Removal)
        label_im, nb_labels = ndimage.label(glued_mask)
        
        if nb_labels > 1:
            sizes = ndimage.sum(glued_mask, label_im, range(nb_labels + 1))
            largest_label = np.argmax(sizes)
            # We keep the area belonging to the largest island
            keep_area = (label_im == largest_label)
            # Apply that "keep area" back to our original sharp mask
            final_mask = mask & keep_area
        else:
            final_mask = mask

        # 4. RE-ADD THE TOP EDGES (The White-on-White Fix)
        height, width = data.shape[:2]
        top_zone = int(height * 0.2)
        not_pure_white = (r < 252) & (g < 252) & (b < 252)
        
        for col in range(width):
            if np.any(final_mask[top_zone:top_zone+150, col]): 
                final_mask[:top_zone, col] |= not_pure_white[:top_zone, col]

        # 5. FINAL REPAIR
        final_mask = ndimage.binary_fill_holes(final_mask)
        # One last smooth to clean up edges
        final_mask = ndimage.binary_closing(final_mask, structure=np.ones((3,3)))

        # 6. EXPORT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
