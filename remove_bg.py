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

        # 1. GENERATE A ROBUST "SCANNER MASK"
        # Instead of trusting the AI, we define 'background' as anything 
        # that is very close to pure white (the scanner bed).
        # We use 250 as the cutoff for 'white'.
        is_not_white = (r < 250) | (g < 250) | (b < 250)
        
        # 2. THE "BLACK BAR" KILLER
        # The black bar at the top is usually very dark (low values).
        # We ignore very dark pixels that are at the very top of the scan.
        height, width = data.shape[:2]
        top_bar_zone = int(height * 0.08)
        is_not_top_black = np.ones_like(is_not_white)
        is_not_top_black[:top_bar_zone, :] = (r[:top_bar_zone, :] > 50)

        # 3. COMBINE AI + GEOMETRY
        # We keep what the AI found OR anything that is clearly not white background.
        combined_mask = (alpha > 50) | is_not_white
        
        # Apply the top-bar filter
        combined_mask &= is_not_top_black

        # 4. FIND THE MAIN OBJECT (Centering)
        # This removes floating "dust" or distant black bars
        coords = np.argwhere(combined_mask)
        if coords.size > 0:
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            
            # Create a mask that only exists within the product's bounds
            final_mask = np.zeros_like(combined_mask)
            final_mask[y_min:y_max, x_min:x_max] = combined_mask[y_min:y_max, x_min:x_max]
        else:
            final_mask = combined_mask

        # 5. HEAL THE ENVELOPE (Closing the gaps)
        # We fill holes and smooth the edges so white envelopes don't look 'eaten'
        final_mask = ndimage.binary_fill_holes(final_mask)
        final_mask = ndimage.binary_closing(final_mask, structure=np.ones((5,5)))

        # 6. FORCE TRANSPARENT BORDER (Fixes the .8 Scaling)
        # We clear the outer 10 pixels to ensure Sharp sees the object correctly
        final_mask[:10, :] = 0
        final_mask[-10:, :] = 0
        final_mask[:, :10] = 0
        final_mask[:, -10:] = 0

        # 7. EXPORT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
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
