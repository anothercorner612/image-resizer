import sharp from 'sharp';
import path from 'path';
import { promises as fs } from 'fs';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

// Fix for __dirname in ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class ImageProcessor {
  constructor(config) {
    this.config = config;
    this.pythonPath = 'python3'; 
    this.scriptPath = path.join(__dirname, '..', 'remove_bg.py');  }

  // RENAMED from 'process' to 'processImage' to match test_run.js
  async processImage(inputBuffer, context = {}) {
    console.log(`[DEBUG] Step 1: Writing temp files for ${context.title || 'image'}...`);
    const tempInput = path.join(__dirname, `temp_in_${Date.now()}.png`);
    const tempOutput = path.join(__dirname, `temp_out_${Date.now()}.png`);

    try {
      await fs.writeFile(tempInput, inputBuffer);

      console.log(`[DEBUG] Step 2: Running Python background removal...`);
      await this.runPythonRemoveBg(tempInput, tempOutput);

      console.log(`[DEBUG] Step 3: Sharp processing (trim/resize/canvas)...`);
      let processedImage = sharp(tempOutput);
      const trimmedBuffer = await processedImage.trim().toBuffer();
      const metadata = await sharp(trimmedBuffer).metadata();

      const canvasWidth = parseInt(this.config.canvasWidth) || 2000;
      const canvasHeight = parseInt(this.config.canvasHeight) || 2500;
      
      const targetHeight = Math.round(canvasHeight * 0.8);
      const scale = targetHeight / metadata.height;
      const targetWidth = Math.round(metadata.width * scale);

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
      .webp({ quality: 85 }) // Matching the expected output format
      .toBuffer();

      // Return the object format that test_run.js expects for its results
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
      await fs.unlink(tempInput).catch(() => {});
      await fs.unlink(tempOutput).catch(() => {});
    }
  }

  runPythonRemoveBg(input, output) {
    return new Promise((resolve, reject) => {
      const py = spawn(this.pythonPath, [this.scriptPath, input, output]);
      
      // Capture Python errors or print statements
      py.stderr.on('data', (data) => console.log(`[PYTHON]: ${data}`));
      py.stdout.on('data', (data) => console.log(`[PYTHON]: ${data}`));

      py.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error(`Python script failed with code ${code}`));
      });
    });
  }

  async getImageDimensions(buffer) {
    const metadata = await sharp(buffer).metadata();
    return { width: metadata.width, height: metadata.height };
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
