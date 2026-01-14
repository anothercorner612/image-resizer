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

        # 1. CORE MASK: High threshold to block "faint" background artifacts
        core_mask = (alpha > 120)

        # 2. TARGETED TOP RECOVERY (Fixes the beheaded white books)
        # We only look at the top 20% of the image
        height, width = data.shape[:2]
        top_zone = int(height * 0.2)
        # Accept pixels that aren't pure white background (luminance check)
        not_pure_white = (r < 252) & (g < 252) & (b < 252)
        
        top_recovery = np.zeros_like(core_mask)
        # Vertical Anchor: Only recover top pixels if there is a "body" below them
        for col in range(width):
            if np.any(core_mask[top_zone:top_zone+100, col]): 
                top_recovery[:top_zone, col] = not_pure_white[:top_zone, col]

        # 3. CONSOLIDATION
        combined = core_mask | top_recovery
        
        # 4. ISLAND REMOVAL (Fixes the "Black Wings" and floating artifacts)
        # This identifies distinct blobs. We only keep the biggest one (the product).
        label_im, nb_labels = ndimage.label(combined)
        if nb_labels > 1:
            sizes = ndimage.sum(combined, label_im, range(nb_labels + 1))
            mask_size = sizes < (sizes.max() * 0.5) # Reject blobs smaller than 50% of main product
            remove_pixel = mask_size[label_im]
            combined[remove_pixel] = 0

        # 5. STRUCTURAL INTEGRITY
        # Closes small gaps in text (Cycling Lexicon) and fills internal holes
        final_mask = ndimage.binary_fill_holes(combined)
        
        # 6. FINAL RECONSTRUCT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
