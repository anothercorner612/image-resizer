#!/usr/bin/env python3
"""
Python wrapper for withoutbg background removal with advanced edge processing
Includes bold color detection for challenging products like multi-colored books
Called by Node.js via subprocess
"""

import sys
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
import withoutbg

def remove_background(input_path, output_path):
    """
    Remove background from image using withoutbg with advanced alpha channel processing

    Args:
        input_path: Path to input image
        output_path: Path to save output image

    Returns:
        0 on success, 1 on error
    """
    try:
        # Verify input file exists
        if not os.path.exists(input_path):
            print(f"Error: Input file not found: {input_path}", file=sys.stderr)
            return 1

        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Initialize withoutbg with opensource models
        print(f"Initializing withoutbg opensource model...", file=sys.stderr)
        model = withoutbg.WithoutBG.opensource()
        
        print(f"Processing: {input_path}", file=sys.stderr)
        result_image = model.remove_background(input_path)
        img_rgba = result_image.convert("RGBA")

        data = np.array(img_rgba)
        alpha = data[:, :, 3]
        rgb = data[:, :, 0:3]

        # 1. ANALYZE: Detect Bold/Solid Colors (like multi-colored books)
        # We look for high-saturation areas that the AI might have skipped
        r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
        saturation = np.max(rgb, axis=2) - np.min(rgb, axis=2)
        bold_color_mask = saturation > 40  # Detects vivid colors even if AI missed them

        # 2. STRATEGIC MASKING
        # Combine the AI's alpha with our bold color detection
        combined_mask = (alpha > 5) | bold_color_mask

        # 3. THE "BRIDGE" LOGIC
        # This connects separate product sections (e.g., top/bottom of split-color books)
        struct = ndimage.generate_binary_structure(2, 2)
        # 8 iterations provides enough 'reach' to bridge horizontal gaps
        mask = ndimage.binary_closing(combined_mask, structure=struct, iterations=8)
        mask = ndimage.binary_fill_holes(mask)

        # 4. RECONSTRUCT ALPHA
        # Apply the solid mask while preserving smooth edges where they existed
        data[:, :, 3] = (mask * 255).astype(np.uint8)

        final_image = Image.fromarray(data)

        # 5. FINAL POLISH
        # Light Gaussian blur prevents edges from looking pixelated on 2000x2500 canvas
        final_image = final_image.filter(ImageFilter.GaussianBlur(radius=0.4))

        final_image.save(output_path)

        # Verify output was created
        if not os.path.exists(output_path):
            print(f"Error: Output file not created: {output_path}", file=sys.stderr)
            return 1

        print(f"Success: {output_path}", file=sys.stderr)
        return 0

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: remove_bg.py <input_path> <output_path>", file=sys.stderr)
        sys.exit(1)
    sys.exit(remove_background(sys.argv[1], sys.argv[2]))
