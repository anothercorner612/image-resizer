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
      await fs.writeFile(tempInput, inputBuffer);

      console.log(`[DEBUG] Step 2: Running Python background removal for ${context.title || 'image'}...`);
      await this.runPythonRemoveBg(tempInput, tempOutput);

      // --- FIX: Added threshold to trim to ignore stray pixels ---
      const trimmedBuffer = await sharp(tempOutput)
        .trim({ threshold: 10 }) 
        .toBuffer();
        
      const metadata = await sharp(trimmedBuffer).metadata();

      const canvasWidth = parseInt(this.config.canvasWidth) || 2000;
      const canvasHeight = parseInt(this.config.canvasHeight) || 2500;
      const maxAllowedWidth = Math.round(canvasWidth * 0.75); 
      const maxAllowedHeight = Math.round(canvasHeight * 0.75);

      let targetHeight = maxAllowedHeight;
      let scale = targetHeight / metadata.height;
      let targetWidth = Math.round(metadata.width * scale);

      if (targetWidth > maxAllowedWidth) {
        targetWidth = maxAllowedWidth;
        scale = targetWidth / metadata.width;
        targetHeight = Math.round(metadata.height * scale);
      }

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
}
