import os
import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

# --- CONFIG ---
HF_TOKEN = os.getenv("HF_TOKEN")
INPUT_FOLDER = "/Users/leefrank/Desktop/test_batch"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/BRIA_COMPARE"
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

def save_variant(img, mask_np, name, suffix):
    mask_pil = Image.fromarray((mask_np * 255).astype(np.uint8)).resize(img.size, Image.LANCZOS)
    res = img.convert("RGBA")
    res.putalpha(mask_pil)
    res.save(os.path.join(OUTPUT_FOLDER, f"{name}_{suffix}.png"))

def run_battle():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    for img_name in files:
        print(f"🕵️‍♂️ Processing 5-way test: {img_name}")
        img_path = os.path.join(INPUT_FOLDER, img_name)
        orig = Image.open(img_path)
        base = os.path.splitext(img_name)[0]

        # 1. STANDARD (The baseline)
        m1 = get_mask(orig, size=1024)
        save_variant(orig, m1, base, "1_STD")

        # 2. LADDER-SPECIFIC (High-Res Detail)
        m2 = get_mask(orig, size=1280)
        save_variant(orig, m2, base, "2_DETAIL")

        # 3. GAMMA-CRUSH (The Fog Killer - keeps edges soft but clears background)
        m3 = np.power(m1, 1.8) 
        save_variant(orig, m3, base, "3_GAMMA")

        # 4. DUAL-FUSION (Blends 768px for body and 1280px for edge)
        m4_low = get_mask(orig, size=768)
        m4_fused = (m4_low + m2) / 2
        save_variant(orig, m4_fused, base, "4_FUSION")

        # 5. HARD-CUT (Geometric/Sticker look)
        m5 = np.where(m1 > 0.3, 1.0, 0.0)
        save_variant(orig, m5, base, "5_HARD")

if __name__ == "__main__":
    run_battle()
    print(f"\n✅ All versions saved to: {OUTPUT_FOLDER}")
