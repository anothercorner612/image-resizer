import sharp from 'sharp';
import path from 'path';
import { promises as fs } from 'fs';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class ImageProcessor {
  constructor(config) {
    this.config = config;
    this.pythonPath = process.env.PYTHON_PATH || 'python3';
    this.scriptPath = path.resolve(__dirname, '..', 'remove_bg.py');
  }

  async processImage(inputBuffer, context = {}) {
    const tempInput = path.join(__dirname, `temp_in_${Date.now()}.png`);
    const tempOutput = path.join(__dirname, `temp_out_${Date.now()}.png`);

    try {
      // 1. Write Input File
      await fs.writeFile(tempInput, inputBuffer);

      console.log(`[DEBUG] Step 2: Running Python background removal for ${context.title || 'image'}...`);
      await this.runPythonRemoveBg(tempInput, tempOutput);

      // --- SAFETY CHECK: Ensure Python actually created the file ---
      try {
        await fs.access(tempOutput);
      } catch {
        throw new Error("Python script failed to generate an output file.");
      }

      // 2. Create Sharp Pipeline (Load once)
      // We create the pipeline but don't execute it yet
      const imagePipeline = sharp(tempOutput);

      // 3. Trim & Get Metadata Efficiently
      // We trim the 'safety gutter' from Python (threshold 10 removes near-transparent pixels)
      const trimmedBuffer = await imagePipeline
        .trim({ threshold: 10 }) 
        .toBuffer();

      // Get metadata from the trimmed buffer
      const metadata = await sharp(trimmedBuffer).metadata();

      // --- SAFETY CHECK: Did we trim everything away? ---
      if (!metadata.width || !metadata.height) {
         throw new Error("Background removal resulted in an empty image (everything was trimmed).");
      }

      // 4. Calculate Scaling (Your Logic)
      const canvasWidth = parseInt(this.config.canvasWidth) || 2000;
      const canvasHeight = parseInt(this.config.canvasHeight) || 2500;
      const maxAllowedWidth = Math.round(canvasWidth * 0.75); 
      const maxAllowedHeight = Math.round(canvasHeight * 0.75);

      let targetHeight = maxAllowedHeight;
      let scale = targetHeight / metadata.height;
      let targetWidth = Math.round(metadata.width * scale);

      // Width Constraint Check
      if (targetWidth > maxAllowedWidth) {
        targetWidth = maxAllowedWidth;
        scale = targetWidth / metadata.width;
        targetHeight = Math.round(metadata.height * scale);
      }

      // 5. Resize & Composite
      // We use the already-trimmed buffer
      const resizedProduct = await sharp(trimmedBuffer)
        .resize(targetWidth, targetHeight)
        .toBuffer();

      const finalBuffer = await sharp({
        create: {
          width: canvasWidth,
          height: canvasHeight,
          channels: 4,
          background: this.config.backgroundColor || '#f3f3f4'
        }
      })
      .composite([{
        input: resizedProduct,
        gravity: 'center'
      }])
      .webp({ quality: 92 })
      .toBuffer();

      return {
        buffer: finalBuffer,
        scalingInfo: {
          scaleFactor: scale,
          originalSize: { width: metadata.width, height: metadata.height },
          targetSize: { width: targetWidth, height: targetHeight }
        }
      };

    } catch (error) {
      console.error(`[DEBUG] Error in ImageProcessor:`, error.message);
      throw error;
    } finally {
      // 6. Cleanup
      await Promise.all([
        fs.unlink(tempInput).catch(() => {}),
        fs.unlink(tempOutput).catch(() => {})
      ]);
    }
  }

  runPythonRemoveBg(input, output) {
    return new Promise((resolve, reject) => {
      const py = spawn(this.pythonPath, [this.scriptPath, input, output]);
      
      // Log Python output for debugging
      py.stderr.on('data', (data) => console.log(`[PYTHON]: ${data}`));
      // py.stdout.on('data', (data) => console.log(`[PYTHON]: ${data}`)); // Optional: Enable if needed
      
      py.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error(`Python script failed with code ${code}`));
      });
    });
  }
}
