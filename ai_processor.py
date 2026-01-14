import io
import os
from rembg import remove, new_session
from PIL import Image

# 1. Initialize the session ONCE. 
# u2net is the 'Cookie Cutter' model best for books and retail goods.
try:
    session = new_session("u2net")
except Exception as e:
    print(f"Error loading AI model: {e}")
    session = None

def process_retail_image(input_bytes):
    """
    The 'Engine': Takes raw bytes, returns clean WebP bytes.
    Optimized for Books, Cards, and Coffee Bags.
    """
    if session is None:
        return input_bytes

    try:
        # AI Extraction: 
        # alpha_matting=False keeps book edges sharp.
        # post_process_mask=True prevents 'gutting' the artwork.
        output_data = remove(
            input_bytes, 
            session=session,
            alpha_matting=False,
            post_process_mask=True 
        )
        
        # Load result and auto-trim empty space
        img = Image.open(io.BytesIO(output_data)).convert("RGBA")
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
            
        # Convert to WebP for Shopify
        out_io = io.BytesIO()
        img.save(out_io, format="WEBP", lossless=True)
        return out_io.getvalue()

    except Exception as e:
        # If one image fails, return None so your tool can log it and move on
        print(f"Skipping image due to error: {e}")
        return None

# --- EXAMPLE OF INTEGRATION WITH YOUR TOOL ---
# for product in active_shopify_products:
#     raw_img = download_image(product.url)
#     processed_img = process_retail_image(raw_img)
#     if processed_img:
#         upload_to_shopify(processed_img)
#         update_metafield(product.id, "processed", True)
