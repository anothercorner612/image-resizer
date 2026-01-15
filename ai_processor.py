import os
import torch
import numpy as np
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms
from transparent_background import Remover
from carvekit.api.high import HiInterface
from dis_bg_remover import remove_background as dis_remove
from rembg import remove, new_session

# --- CONFIG ---
INPUT_FOLDER = "/Users/leefrank/Desktop/test"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/ULTIMATE_BATTLE"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# 1. Load Bria RMBG-2.0
print("⏳ Loading Bria RMBG-2.0...")
bria_model = AutoModelForImageSegmentation.from_pretrained('briaai/RMBG-2.0', trust_remote_code=True).to(device).eval()

# 2. Load BiRefNet (via rembg session for stability)
print("⏳ Loading BiRefNet...")
biref_session = new_session("birefnet-general")

# 3. Load InSPyReNet (transparent-background)
print("⏳ Loading InSPyReNet...")
inspyre_remover = Remover()

# 4. Load CarveKit
print("⏳ Loading CarveKit...")
carve_interface = HiInterface(object_type="object", device=device)

# --- HELPER: Process Bria ---
def run_bria(img):
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    input_tensor = transform(img.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        preds = bria_model(input_tensor)[-1].sigmoid().cpu()
    mask = transforms.ToPILImage()(preds[0].squeeze()).resize(img.size)
    res = img.convert("RGBA")
    res.putalpha(mask)
    return res

def process_all():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for img_name in files:
        print(f"⚔️ Battling: {img_name}")
        path = os.path.join(INPUT_FOLDER, img_name)
        original = Image.open(path).convert("RGB")
        base = os.path.splitext(img_name)[0]

        # 1. Bria RMBG-2.0
        bria_out = run_bria(original)
        bria_out.save(os.path.join(OUTPUT_FOLDER, f"{base}_1_BRIA.png"))

        # 2. BiRefNet
        biref_out = remove(original, session=biref_session)
        biref_out.save(os.path.join(OUTPUT_FOLDER, f"{base}_2_BIREF.png"))

        # 3. InSPyReNet
        insp_raw = inspyre_remover.process(original, type='rgba')
        Image.fromarray(insp_raw).save(os.path.join(OUTPUT_FOLDER, f"{base}_3_INSPYRE.png"))

        # 4. CarveKit
        carve_out = carve_interface([original])[0]
        carve_out.save(os.path.join(OUTPUT_FOLDER, f"{base}_4_CARVEKIT.png"))

        # 5. DIS (Note: Requires local .onnx path, skipping direct script call for speed)
        print(f"✅ {img_name} batch complete.")

if __name__ == "__main__":
    process_all()
