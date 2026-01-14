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
        
        # 1. CORE MASK: Start with what the AI is sure about
        # We use a lower threshold (50) to catch faint edges
        mask = (alpha > 50).astype(np.uint8)

        # 2. THE BOOK-SAVER (Vertical Dilation)
        # We expand the mask specifically UPWARD. This forces the script
        # to re-examine the area where the book was "beheaded."
        structure = np.zeros((20, 1)) 
        structure[:10, 0] = 1 # Look 10 pixels up
        refined_mask = ndimage.binary_dilation(mask, structure=structure).astype(np.uint8)
        
        # 3. RE-VALIDATE: Only keep the "expanded" pixels if they aren't pure white
        # This prevents the mask from just growing into the empty background
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
        is_not_pure_white = (r < 245) | (g < 245) | (b < 245)
        
        final_mask = np.where(refined_mask & is_not_pure_white, 1, mask)
        
        # 4. HOLE FILLING
        # Closes the gaps in the 'Cycling Lexicon' and 'Thank You' card
        final_mask = ndimage.binary_fill_holes(final_mask).astype(np.uint8)

        # 5. FINAL RECONSTRUCT
        data[:, :, 3] = (final_mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background(sys.argv[1], sys.argv[2]))
