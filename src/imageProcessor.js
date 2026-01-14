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
    // Path is now fixed to the root folder
    this.scriptPath = path.resolve(__dirname, '..', 'remove_bg.py');
  }

  /**
   * Main processing pipeline: Remove BG -> Trim -> Resize to Fit -> Composite
   */
  async processImage(inputBuffer, context = {}) {
    const tempInput = path.join(__dirname, `temp_in_${Date.now()}.png`);
    const tempOutput = path.join(__dirname, `temp_out_${Date.now()}.png`);

    try {
      // 1. Prepare files for Python
      await fs.writeFile(tempInput, inputBuffer);

      // 2. Remove Background via Python
      console.log(`[DEBUG] Step 2: Running Python background removal for ${context.title || 'image'}...`);
      await this.runPythonRemoveBg(tempInput, tempOutput);

      // 3. Trim whitespace and get dimensions
      const trimmedBuffer = await sharp(tempOutput).trim().toBuffer();
      const metadata = await sharp(trimmedBuffer).metadata();

      // 4. Calculate Canvas Scaling (Ensures image never exceeds canvas bounds)
      const canvasWidth = parseInt(this.config.canvasWidth) || 2000;
      const canvasHeight = parseInt(this.config.canvasHeight) || 2500;
      const maxAllowedWidth = Math.round(canvasWidth * 0.85); // 85% safety margin
      const maxAllowedHeight = Math.round(canvasHeight * 0.85);

      let targetHeight = maxAllowedHeight;
      let scale = targetHeight / metadata.height;
      let targetWidth = Math.round(metadata.width * scale);

      // Width-check: If product is too wide, scale based on width instead
      if (targetWidth > maxAllowedWidth) {
        targetWidth = maxAllowedWidth;
        scale = targetWidth / metadata.width;
        targetHeight = Math.round(metadata.height * scale);
      }

      // 5. Resize and Composite onto final canvas
      const resizedProduct = await sharp(trimmedBuffer)
        .resize(targetWidth, targetHeight)
        .toBuffer();

      const finalBuffer = await sharp({
        create: {
          width: canvasWidth,
          height: canvasHeight,
          channels: 4,
          background: this.config.backgroundColor || '#f2f2f2'
        }
      })
      .composite([{
        input: resizedProduct,
        gravity: 'center'
      }])
      .webp({ quality: 85 })
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
      // Cleanup temp files immediately
      await Promise.all([
        fs.unlink(tempInput).catch(() => {}),
        fs.unlink(tempOutput).catch(() => {})
      ]);
    }
  }

  runPythonRemoveBg(input, output) {
    return new Promise((resolve, reject) => {
      const py = spawn(this.pythonPath, [this.scriptPath, input, output]);

      py.stderr.on('data', (data) => console.log(`[PYTHON]: ${data}`));
      py.stdout.on('data', (data) => console.log(`[PYTHON]: ${data}`));

      py.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error(`Python script failed with code ${code}`));
      });
    });
  }

  async isValidImage(buffer) {
    try {
      await sharp(buffer).metadata();
      return true;
    } catch (e) {
      return false;
    }
  }
}
