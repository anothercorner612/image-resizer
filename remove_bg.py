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

        # 1. BRIGHTNESS PROTECTOR (Keep dark covers solid)
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)

        # 2. THE CORE MASK
        # Protect dark pixels (cover) but keep AI's general shape
        mask = (alpha > 140) | ((brightness < 60) & (alpha > 50))

        # 3. GEOMETRIC LOCK (Find the book's width)
        coords = np.argwhere(mask)
        if coords.size > 0:
            x_min = coords[:, 1].min()
            x_max = coords[:, 1].max()
            # Add a small buffer so we don't clip the very edge pixels
            x_min = max(0, x_min - 5)
            x_max = min(data.shape[1], x_max + 5)
        else:
            x_min, x_max = 0, data.shape[1]

        # 4. TOP RECOVERY (The White-on-White fix)
        height, width = data.shape[:2]
        top_zone = int(height * 0.20)
        not_bg_white = (r < 250) & (g < 250) & (b < 250)
        
        for col in range(x_min, x_max):
            if np.any(mask[top_zone:top_zone+150, col]): 
                mask[:top_zone, col] |= not_bg_white[:top_zone, col]

        # 5. SHADOW EROSION (Clean the bottom bar)
        bottom_edge = int(height * 0.85)
        mask[bottom_edge:, :] = ndimage.binary_erosion(mask[bottom_edge:, :], iterations=2)

        # 6. STRUCTURAL CLEANUP
        mask = ndimage.binary_fill_holes(mask)
        mask = ndimage.binary_closing(mask, structure=np.ones((3,3)))

        # 7. FINAL CLIP (Remove anything outside the book width)
        final_mask = np.zeros_like(mask)
        final_mask[:, x_min:x_max] = mask[:, x_min:x_max]

        # 8. EXPORT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        # CRITICAL: If Python fails, save the raw AI image so Sharp doesn't crash
        print(f"Python Error: {e}", file=sys.stderr)
        if 'result_image' in locals():
            result_image.save(output_path)
        return 0 # Return 0 so the JS runner continues

if __name__ == "__main__":
    if len(sys.argv)
