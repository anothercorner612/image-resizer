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

        # 1. DEFINE "TRUE" BACKGROUND
        # Anything very close to the scanner-bed white is background.
        # We use 253 to be extremely precise.
        is_pure_white = (r > 252) & (g > 252) & (b > 252)
        
        # 2. THE MASK (Safety First)
        # Keep what the AI found, BUT if it's pure white, make it transparent.
        # Keep everything else that isn't pure white.
        mask = (alpha > 50) | (~is_pure_white)

        # 3. TOP/BOTTOM CLEANER (The Black Bar Fix)
        # Instead of deleting islands, we just 'shave' the very edges where 
        # scanner bars and shadows usually live.
        height, width = data.shape[:2]
        # Force a 2% crop at top and bottom to kill hinge shadows
        edge_h = int(height * 0.02)
        mask[:edge_h, :] = 0
        mask[-edge_h:, :] = 0

        # 4. HOLE FILLING (Protects the envelope)
        # This fills in any "eaten" spots in the middle of the book or envelope.
        mask = ndimage.binary_fill_holes(mask)
        # Smooth the edges slightly
        mask = ndimage.binary_closing(mask, structure=np.ones((3,3)))

        # 5. GEOMETRIC BOUNDS (For the .8 Scaling)
        # Find the product, then clear a 15px buffer around it.
        coords = np.argwhere(mask)
        if coords.size > 0:
            y_min, x_min = coords.min(axis=0), coords.min(axis=1) # wait, correction:
            y_min, x_min = coords[:, 0].min(), coords[:, 1].min()
            y_max, x_max = coords[:, 0].max(), coords[:, 1].max()
            
            cleaned_mask = np.zeros_like(mask)
            # Add a 5px safety padding so we don't clip the book's actual edge
            cleaned_mask[max(0, y_min-5):min(height, y_max+5), 
                         max(0, x_min-5):min(width, x_max+5)] = mask[max(0, y_min-5):min(height, y_max+5), 
                                                                    max(0, x_min-5):min(width, x_max+5)]
            mask = cleaned_mask

        # 6. FINAL SHARP BORDER
        # This is the "Handshake" that tells JavaScript exactly where the book is.
        mask[:10, :] = 0
        mask[-10:, :] = 0
        mask[:, :10] = 0
        mask[:, -10:] = 0

        # 7. EXPORT
        data[:, :, 3] = (mask * 255).astype(np.uint8)
        Image.fromarray(data).save(output_path)
        return 0

    except Exception as e:
        print(f"Python Error: {e}", file=sys.stderr)
        if 'result_image' in locals():
            result_image.save(output_path)
        return 0

if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(remove_background
