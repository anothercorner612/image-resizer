import sys
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    try:
        # 1. Initialization
        if not os.path.exists(input_path):
            return 1

        # Initialize the model (using the lowercase call we verified)
        model = withoutbg.WithoutBG.opensource()
        
        # 2. Get initial AI Alpha Mask
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")
        data = np.array(img_rgba)
        
        # Split channels
        rgb = data[:, :, 0:3]
        alpha = data[:, :, 3]

        # 3. ADVANCED DETECTION (The Fix for the Black Book)
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
        # Luminance identifies dark objects that AI often mistakes for "void"
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        # Saturation identifies vivid colors that should never be removed
        saturation = np.max(rgb, axis=2) - np.min(rgb, axis=2)
        
        # Create a "Product Safety Mask" 
        # Keep if AI says so OR if it's very dark (Black Book) OR if it's vivid
        combined_mask = (alpha > 10) | (luminance < 50) | (saturation > 30)

        # 4. ARTIFACT CLEANUP (The Fix for the Calendar Bars)
        # Label separate 'islands' of pixels
        label_im, nb_labels = ndimage.label(combined_mask)
        if nb_labels > 1:
            # Find the size of the largest island (the actual product)
            sizes = ndimage.sum(combined_mask, label_im, range(nb_labels + 1))
            # Remove any island that is less than 15% of the main product's size
            mask_size = sizes < (sizes.max() * 0.15)
            remove_pixel = mask_size[label_im]
            combined_mask[remove_pixel] = 0

        # 5. THE BRIDGE & HOLE FILLING
        # This keeps the product solid and fills any "internal" AI errors
        struct = ndimage.generate_binary_structure(2, 2)
        mask = ndimage.binary_closing(combined_mask, structure=struct, iterations=4)
        mask = ndimage.binary_fill_holes(mask)

        # 6. RECONSTRUCT & POLISH
        data[:, :, 3] = (mask * 255).astype(np.uint8)
        final_image = Image.fromarray(data)
        
        # Sharpness Fix: Reduced blur to 0.15 to keep text crisp on book covers
        final_image = final_image.filter(ImageFilter.GaussianBlur(radius=0.15))

        final_image.save(output_path)
        return 0

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
