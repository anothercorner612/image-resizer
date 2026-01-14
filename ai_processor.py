import os
from rembg import remove
from PIL import Image
import io

input_folder = "/Users/leefrank/Desktop/test"
output_folder = "ai_test_results"
os.makedirs(output_folder, exist_ok=True)

for img_name in os.listdir(input_folder):
    if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
        print(f"Processing {img_name} with AI...")
        input_path = os.path.join(input_folder, img_name)
        
        with open(input_path, 'rb') as i:
            input_data = i.read()
            # This is the AI magic
            output_data = remove(input_data)
            
            img = Image.open(io.BytesIO(output_data)).convert("RGBA")
            
            # Here we add your white canvas request
            canvas = Image.new("RGBA", (2000, 2000), (255, 255, 255, 255))
            
            # Resize product to fit 85% of canvas
            max_dim = 1700 
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            # Center it
            x = (2000 - img.size[0]) // 2
            y = (2000 - img.size[1]) // 2
            canvas.paste(img, (x, y), img)
            
            canvas.save(os.path.join(output_folder, f"{os.path.splitext(img_name)[0]}_FINAL.png"))

print("Done! Check the ai_test_results folder.")
