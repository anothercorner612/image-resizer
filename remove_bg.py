import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    try:
        # Initialize the model
        model = withoutbg.WithoutBG.opensource()
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")
        data = np.array(img_rgba)
        
        alpha = data[:, :, 3]
        rgb = data[:, :, 0:3]
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]

        # 1. THE PRECISION MASK
        # Force a high threshold to ignore faint shadows and artifacts
        core_mask = (alpha > 120)

        # 2. WHITE TOP RECOVERY (The White Book/Green Pattern Fix)
        # Specifically target the top 30% of the image to look for missing white edges
        height = data.shape[0]
        top_zone_height = int(height * 0.3)
        
        # Look for pixels that are NOT pure background white (e.g., paper/cover colors)
        not_pure_white = (r < 252) & (g < 252) & (b < 252)
        
        # Create a blank recovery mask and only fill the top zone
        top_recovery = np.zeros_like(core_mask)
        top_recovery[:top_zone_height, :] = not_pure_white[:top_zone_height, :]
        
        # 3. COMBINE & CLEAN
        # Keep everything the AI is sure about, PLUS anything at the top that isn't background
        combined = core_mask | top_recovery
        
        # Remove tiny "specs" of noise
        combined = ndimage.binary_opening(combined, structure=np.ones((3,3)))
        
        # Fill in the center of the hand/books (The 'Cycling Lexicon' Fix)
        final_mask = ndimage.binary_fill_holes(combined)

        # 4. FINAL RECONSTRUCT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0
        
    except Exception as e:
        print(f"Error in Python: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
