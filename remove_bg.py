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
        r, g, b = data[:,:,0], data[:,:,1], data[:,:,2]

        # 1. BRIGHTNESS CALCULATION
        # This helps us distinguish between a "flat" black shadow and a "detailed" black cover
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)

        # 2. THE CORE MASK
        # We start with the AI mask but PROTECT anything that is quite dark (likely the book)
        # and REJECT anything that is medium-gray (likely the shadow)
        mask = (alpha > 140) | ((brightness < 60) & (alpha > 50))

        # 3. GEOMETRIC LOCK (Horizontal)
        coords = np.argwhere(mask)
        if coords.size > 0:
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
        else:
            x_min, x_max = 0, data.shape[1]

        # 4. TOP RECOVERY (The White-on-White fix)
        height, width = data.shape[:2]
        top_zone = int(height * 0.20)
        not_bg_white = (r < 250) & (g < 250) & (b < 250)
        
        for col in range(x_min, x_max):
            # Only recover top if there is body below
            if np.any(mask[top_zone:top_zone+150, col]): 
                mask[:top_zone, col] |= not_bg_white[:top_zone, col]

        # 5. THE SHADOW KILLER (Bottom-Up Erosion)
        # Most "black bars" are at the very bottom. We erode just the bottom edge.
        bottom_edge = int(height * 0.85)
        mask[bottom_edge:, :] = ndimage.binary_erosion(mask[bottom_edge:, :], iterations=2)

        # 6. STRUCTURAL INTEGRITY
        mask = ndimage.binary_fill_holes(mask)
        mask = ndimage.binary_closing(mask, structure=np.ones((3,3)))

        # 7. FINAL CLIP
        final_mask = np.zeros_like(mask)
        final_mask[:, x_min:x_max] = mask[:, x_min:x_max]

        # 8. EXPORT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
