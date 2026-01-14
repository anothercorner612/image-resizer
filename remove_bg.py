import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    try:
        # 1. AI SEGMENTATION
        model = withoutbg.WithoutBG.opensource()
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")
        data = np.array(img_rgba)
        
        alpha = data[:, :, 3]
        rgb = data[:, :, 0:3]
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]

        # 2. THE CORE MASK
        # We use a high threshold (125) to stop shadows from turning into solid blocks
        mask = (alpha > 125)

        # 3. VERTICAL RECOVERY (The "White Book" Fix)
        # We only look at the top 20% for missing white edges
        height, width = data.shape[:2]
        top_zone = int(height * 0.2)
        not_pure_white = (r < 252) & (g < 252) & (b < 252)
        
        top_recovery = np.zeros_like(mask)
        # VERTICAL ANCHOR: Only recover if there is a 'body' in that same column
        for col in range(width):
            if np.any(mask[top_zone:top_zone+120, col]): 
                top_recovery[:top_zone, col] = not_pure_white[:top_zone, col]

        # 4. COMPONENT ANALYSIS (The "Wing" & Artifact Killer)
        # This finds separate 'blobs'. It deletes everything except the biggest one.
        combined = mask | top_recovery
        label_im, nb_labels = ndimage.label(combined)
        
        if nb_labels > 1:
            sizes = ndimage.sum(combined, label_im, range(nb_labels + 1))
            # Keep only the largest object (index of the max size)
            largest_label = np.argmax(sizes)
            final_mask = (label_im == largest_label)
        else:
            final_mask = combined

        # 5. STRUCTURAL INTEGRITY
        # Fill internal holes (text/details) and smooth the edge slightly
        final_mask = ndimage.binary_fill_holes(final_mask)
        # Closing joins any tiny cracks in the mask
        final_mask = ndimage.binary_closing(final_mask, structure=np.ones((3,3)))

        # 6. SAVE OUTPUT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        print(f"Error in Python: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
