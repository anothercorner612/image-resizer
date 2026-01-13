#!/usr/bin/env python3
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from withoutbg import WithoutBG

def remove_background(input_path, output_path):
    try:
        model = WithoutBG.opensource()
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")
        
        data = np.array(img_rgba)
        alpha = data[:, :, 3]
        rgb = data[:, :, 0:3]

        # 1. ANALYZE: Detect Bold/Solid Colors (like the Red Book)
        # We look for high-saturation areas that the AI might have skipped
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
        saturation = np.max(rgb, axis=2) - np.min(rgb, axis=2)
        bold_color_mask = saturation > 40  # Detects vivid colors even if AI missed them

        # 2. STRATEGIC MASKING
        # Combine the AI's alpha with our bold color detection
        combined_mask = (alpha > 5) | bold_color_mask

        # 3. THE "BRIDGE" LOGIC
        # This connects the top red half to the bottom blue half of the book
        struct = ndimage.generate_binary_structure(2, 2)
        # 8 iterations provides enough 'reach' to bridge the horizontal gap
        mask = ndimage.binary_closing(combined_mask, structure=struct, iterations=8)
        mask = ndimage.binary_fill_holes(mask)

        # 4. RECONSTRUCT ALPHA
        # We apply the solid mask but keep the original smooth edges where they existed
        data[:, :, 3] = (mask * 255).astype(np.uint8)
        
        final_image = Image.fromarray(data)
        
        # 5. FINAL POLISH
        # A light Gaussian blur prevents the edges from looking like "pixels" 
        # on the 2000x2500 canvas.
        final_image = final_image.filter(ImageFilter.GaussianBlur(radius=0.4))
        
        final_image.save(output_path)
        return 0

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(1)
    sys.exit(remove_background(sys.argv[1], sys.argv[2]))
