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

        # --- ADJUSTMENT 1: BRIGHTNESS PROTECTION ---
        # Increased to 85 to protect light-colored cards/envelopes
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)
        
        # --- ADJUSTMENT 2: CORE MASK THRESHOLD ---
        # Dropped Alpha to 70 to keep soft white edges
        mask = (alpha > 70) | ((brightness < 85) & (alpha > 30))

        # 3. GEOMETRIC LOCK
        coords = np.argwhere(mask)
        if coords.size > 0:
            x_min, x_max = coords[:, 1].min(), coords[:, 1].max()
            x_min = max(0, x_min - 15)
            x_max = min(data.shape[1], x_max + 15)
        else:
            x_min, x_max = 0, data.shape[1]

        # 4. ENVELOPE / WHITE EDGE RECOVERY
        height, width = data.shape[:2]
        top_zone = int(height * 0.40) # Look even further down for recovery
        
        # --- ADJUSTMENT 3: RECOVERY SENSITIVITY ---
        # Changed to 253 - captures everything except the most "pure" white
        not_bg_white = (r < 253) & (g < 253) & (b < 253)
        
        for col in range(x_min, x_max):
            if np.any(mask[top_zone:top_zone+250, col]): 
                mask[:top_zone, col] |= not_bg_white[:top_zone, col]

        # 5. STRUCTURAL CLEANUP
        mask = ndimage.binary_fill_holes(mask)
        # Smaller structure preserves sharp corners of the envelope
        mask = ndimage.binary_closing(mask, structure=np.ones((2,2)))

        # 6. CANVAS CLEANER (Ensures the .8 scaling works)
        final_mask = np.zeros_like(mask)
        final_mask[5:-5, x_min+2:x_max-2] = mask[5:-5, x_min+2:x_max-2]

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
