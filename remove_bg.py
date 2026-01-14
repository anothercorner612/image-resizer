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
        # 125 is the "Sweet Spot" to keep black books solid but kill gray shadows
        mask = (alpha > 125)

        # 3. VERTICAL RECOVERY (Fixes the White-on-White "Beheading")
        # Scans the top 20% specifically for pixels that aren't pure background
        height, width = data.shape[:2]
        top_zone = int(height * 0.2)
        not_pure_white = (r < 252) & (g < 252) & (b < 252)
        
        top_recovery = np.zeros_like(mask)
        # Only recover white edges if they sit directly above the known product body
        for col in range(width):
            if np.any(mask[top_zone:top_zone+120, col]): 
                top_recovery[:top_zone, col] = not_pure_white[:top_zone, col]

        # 4. COMPONENT ANALYSIS (The "Wing" & Artifact Killer)
        # This identifies isolated blobs. We delete everything except the biggest one.
        combined = mask | top_recovery
        label_im, nb_labels = ndimage.label(combined)
        
        if nb_labels > 1:
            sizes = ndimage.sum(combined, label_im, range(nb_labels + 1))
            # Keep only the largest object in the image (the product)
            largest_label = np.argmax(sizes)
            final_mask = (label_im == largest_label)
        else:
            final_mask = combined

        # 5. STRUCTURAL REPAIR
        # Fill holes (fix internal text/details) and smooth the edges
        final_mask = ndimage.binary_fill_holes(final_mask)
        # Fuses tiny gaps and smooths the silhouette
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
