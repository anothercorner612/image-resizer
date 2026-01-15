import os
import torch
import numpy as np
from PIL import Image, ImageEnhance
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- CONFIG ---
HF_TOKEN = "your_token_here" # <--- Update this
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/BRIA_WEBP_COMPARE"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

device = 'mps' if torch.backends.mps.is_available() else 'cpu'
model = AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-2.0', trust_remote_code=True, token=HF_TOKEN).to(device).eval()

def get_mask(img, size=1024, contrast=1.0):
    temp_img = img.convert("RGB")
    if contrast != 1.0: temp_img = ImageEnhance.Contrast(temp_img).enhance(contrast)
    
    t = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    input_tensor = t(temp_img).unsqueeze(0).to(device)
    with torch.no_grad():
        pred = model(input_tensor)[-1].sigmoid().cpu()
    return pred[0].squeeze().numpy()

def save_as_webp(img, mask_np, base_name, suffix):
    mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8)).resize(img.size, Image.LANCZOS)
    res = img.convert("RGBA")
    res.putalpha(mask_pil)
    
    # Save as WebP for speed and smaller file size
    save_path = os.path.join(OUTPUT_FOLDER, f"{base_name}_{suffix}.webp")
    res.save(save_path, "WEBP", quality=90, method=6)

def run_experiment():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    for img_name in files:
        print(f"🕵️‍♂️ Running 5-way WebP test: {img_name}")
        img_path = os.path.join(INPUT_FOLDER, img_name)
        orig = Image.open(img_path)
        base = os.path.splitext(img_name)[0]

        # 1. STANDARD (The Baseline)
        m1 = get_mask(orig, size=1024)
        save_as_webp(orig, m1, base, "1_STD")

        # 2. DETAIL (High-Res 1280px - Targeted at the Ladder)
        m2 = get_mask(orig, size=1280)
        save_as_webp(orig, m2, base, "2_DETAIL")

        # 3. GAMMA (Gamma 1.8 - Clears background fog)
        m3 = np.power(m1, 1.8) 
        save_as_webp(orig, m3, base, "3_GAMMA")

        # 4. FUSION (Blends 768px Body + 1280px Detail)
        m4_low = get_mask(orig, size=768)
        m4_fused = (m4_low + m2) / 2
        save_as_webp(orig, m4_fused, base, "4_FUSION")

        # 5. CONTRAST-HARD (Contrast Boost + Binary Cut)
        m5_mask = get_mask(orig, size=1024, contrast=1.3)
        m5_hard = np.where(m5_mask > 0.35, 1.0, 0.0)
        save_as_webp(orig, m5_hard, base, "5_HARD")

if __name__ == "__main__":
    run_experiment()
    print(f"\n✅ All variations saved to: {OUTPUT_FOLDER}")
