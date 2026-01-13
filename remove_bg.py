#!/usr/bin/env python3
"""
Python wrapper for withoutbg background removal
Called by Node.js via subprocess
"""

import sys
import os
from pathlib import Path
from withoutbg import WithoutBG

def remove_background(input_path, output_path):
    """
    Remove background from image using withoutbg

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
        # First run will download models (~320MB)
        print(f"Initializing withoutBG opensource model...", file=sys.stderr)
        model = WithoutBG.opensource()

        print(f"Processing: {input_path}", file=sys.stderr)
        result_image = model.remove_background(input_path)

        # Save the result
        result_image.save(output_path)

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

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    exit_code = remove_background(input_path, output_path)
    sys.exit(exit_code)
