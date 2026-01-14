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

        # 1. BASE MASK (Ignore light shadows)
        mask = (alpha > 130) 

        # 2. FIND THE HORIZONTAL LIMITS (The "Geometric Lock")
        # This finds the leftmost and rightmost pixel of the actual book body
        coords = np.argwhere(mask)
        if coords.size > 0:
            x_min, x_max = coords[:, 1].min(), coords[:, 1].max()
            # Add a tiny 5px buffer
            x_min = max(0, x_min - 5)
            x_max = min(data.shape[1], x_max + 5)
        else:
            x_min, x_max = 0, data.shape[1]

        # 3. SELECTIVE TOP RECOVERY (Fixes White Blocks)
        height, width = data.shape[:2]
        top_zone = int(height * 0.20)
        not_pure_white = (r < 250) & (g < 250) & (b < 250)
        
        for col in range(x_min, x_max): # ONLY scan within the book's width
            # If there's a body in this column, recover the top
            if np.any(mask[top_zone:top_zone+150, col]): 
                mask[:top_zone, col] |= not_pure_white[:top_zone, col]

        # 4. STRUCTURAL CLEANUP
        # Fill holes in text/leaves and bridge small gaps
        mask = ndimage.binary_dilation(mask, iterations=2)
        mask = ndimage.binary_fill_holes(mask)
        mask = ndimage.binary_erosion(mask, iterations=2)

        # 5. KILL WINGS (Final X-Axis Crop)
        # Any pixel outside the x_min/x_max is forced to transparent
        final_mask = np.zeros_like(mask)
        final_mask[:, x_min:x_max] = mask[:, x_min:x_max]

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
