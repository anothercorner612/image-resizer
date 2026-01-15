import os
import torch
import numpy as np
from PIL import Image
from transformers import AutoModelForImageSegmentation
from torchvision import transforms
from transparent_background import Remover
from carvekit.api.high import HiInterface
from rembg import remove, new_session

# --- CONFIG (The Secure Way) ---
# Set this in terminal first: export HF_TOKEN="your_token"
HF_TOKEN = os.getenv("HF_TOKEN") 

INPUT_FOLDER = "/Users/leefrank/Desktop/test_batch"
OUTPUT_FOLDER = "/Users/leefrank/Desktop/ULTIMATE_BATTLE"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Select Device (Mac M1/M2/M3 uses 'mps', otherwise 'cpu')
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"💻 Using Device: {device.upper()}")

# --- 1. Load Engines ---
print("⏳ Loading Bria RMBG-2.0...")
bria_model = AutoModelForImageSegmentation.from_pretrained(
    'briaai/RMBG-2.0', 
    trust_remote_code=True,
    token=HF_TOKEN
).to(device).eval()

print("⏳ Loading BiRefNet...")
biref_session = new_session("birefnet-general")

print("⏳ Loading InSPyReNet...")
inspyre_remover = Remover()

print("⏳ Loading CarveKit (High-Res)...")
# CarveKit works best on CPU for stability on some Macs, but we'll try device first
carve_interface = HiInterface(object_type="object", batch_size=1, device=device)

# --- Helper: Bria Processing ---
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

# --- Main Battle Loop ---
def start_battle():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    print(f"🚀 Found {len(files)} images. Starting Battle...")

    for img_name in files:
        print(f"\n⚔️  Processing: {img_name}")
        path = os.path.join(INPUT_FOLDER, img_name)
        original = Image.open(path).convert("RGB")
        base = os.path.splitext(img_name)[0]

        # ENGINE 1: Bria RMBG-2.0
        try:
            bria_out = run_bria(original)
            bria_out.save(os.path.join(OUTPUT_FOLDER, f"{base}_1_BRIA.png"))
            print(" ✅ Bria Success")
        except Exception as e: print(f" ❌ Bria Failed: {e}")

        # ENGINE 2: BiRefNet
        try:
            biref_out = remove(original, session=biref_session)
            biref_out.save(os.path.join(OUTPUT_FOLDER, f"{base}_2_BIREFNET.png"))
            print(" ✅ BiRefNet Success")
        except Exception as e: print(f" ❌ BiRefNet Failed: {e}")

        # ENGINE 3: InSPyReNet
        try:
            # transparent-background returns a numpy array
            insp_raw = inspyre_remover.process(original, type='rgba')
            Image.fromarray(np.uint8(insp_raw)).save(os.path.join(OUTPUT_FOLDER, f"{base}_3_INSPYRE.png"))
            print(" ✅ InSPyReNet Success")
        except Exception as e: print(f" ❌ InSPyReNet Failed: {e}")

        # ENGINE 4: CarveKit
        try:
            carve_out = carve_interface([original])[0]
            carve_out.save(os.path.join(OUTPUT_FOLDER, f"{base}_4_CARVEKIT.png"))
            print(" ✅ CarveKit Success")
        except Exception as e: print(f" ❌ CarveKit Failed: {e}")

if __name__ == "__main__":
    start_battle()
    print(f"\n🏁 ALL DONE! Check your results here: {OUTPUT_FOLDER}")
