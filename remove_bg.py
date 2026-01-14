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

        # 1. SCANNER MASK (Anything not pure scanner-white)
        # We use 252 to be very strict about what counts as 'background'
        is_not_white = (r < 252) | (g < 252) | (b < 252)
        
        # 2. INITIAL COMBINED MASK
        combined_mask = (alpha > 80) | is_not_white

        # 3. THE "ISLAND KILLER" (Connectivity Analysis)
        # This identifies every separate 'blob' in the image.
        label_im, nb_labels = ndimage.label(combined_mask)
        if nb_labels > 1:
            # Find the size of every blob
            sizes = ndimage.sum(combined_mask, label_im, range(nb_labels + 1))
            # The largest blob is our product. Everything else is 'dust' or 'bars'.
            mask_largest = (label_im == np.argmax(sizes))
        else:
            mask_largest = combined_mask

        # 4. HEAL AND FILL
        # This ensures the envelope stays solid and corners stay sharp
        final_mask = ndimage.binary_fill_holes(mask_largest)
        final_mask = ndimage.binary_closing(final_mask, structure=np.ones((3,3)))

        # 5. CROP TO CONTENT (Fixes the "Too Small" / Scaling issue)
        # We find the exact edges of the product and 'crop' the mask to it
        coords = np.argwhere(final_mask)
        if coords.size > 0:
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            
            # Wipe everything outside this tight box
            cleaned_mask = np.zeros_like(final_mask)
            cleaned_mask[y_min:y_max, x_min:x_max] = final_mask[y_min:y_max, x_min:x_max]
            
            # Force a 10px buffer of transparency at the VERY edges of the file
            # This is the 'handshake' for the .8 scaling to work perfectly
            cleaned_mask[:10, :] = 0
            cleaned_mask[-10:, :] = 0
            cleaned_mask[:, :10] = 0
            cleaned_mask[:, -10:] = 0
            final_mask = cleaned_mask

        # 6. EXPORT
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
