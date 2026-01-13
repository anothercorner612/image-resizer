import sharp from 'sharp';
import path from 'path';
import { promises as fs } from 'fs';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

dotenv.config();
console.log('--- ENV CHECK ---');
console.log('Store URL:', process.env.SHOPIFY_STORE_URL ? 'FOUND' : 'MISSING');
console.log('Token:', process.env.SHOPIFY_ACCESS_TOKEN ? 'FOUND' : 'MISSING');
console.log('-----------------');

// Standard fix for __dirname in ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class ImageProcessor {
  constructor(config) {
    this.config = config;
    this.pythonPath = 'python3'; 
    this.scriptPath = path.join(__dirname, 'remove_bg.py');
  }

  /**
   * Called by TestRunner.processExamples
   */
  async processImage(inputBuffer, context = {}) {
    const tempInput = path.join(__dirname, `temp_in_${Date.now()}.png`);
    const tempOutput = path.join(__dirname, `temp_out_${Date.now()}.png`);

    try {
      // 1. Save buffer to temp file for Python
      await fs.writeFile(tempInput, inputBuffer);

      // 2. Run Python background removal
      await this.runPythonRemoveBg(tempInput, tempOutput);

      // 3. Load processed result and trim
      let processedImage = sharp(tempOutput);
      const trimmedBuffer = await processedImage.trim().toBuffer();
      const metadata = await sharp(trimmedBuffer).metadata();

      // 4. Create the 2000x2500 Canvas
      const canvasWidth = parseInt(this.config.canvasWidth) || 2000;
      const canvasHeight = parseInt(this.config.canvasHeight) || 2500;
      
      // Scaling: 80% of canvas height
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
      .webp({ quality: 85 }) // Outputting as WebP as per your test_run.js expectations
      .toBuffer();

      // 5. Return in the format test_run.js expects
      return {
        buffer: finalBuffer,
        scalingInfo: {
          reason: 'Standard 80% height scaling',
          aspectRatio: (metadata.width / metadata.height).toFixed(2),
          canvas: { width: canvasWidth, height: canvasHeight },
          scaled: { 
            width: targetWidth, 
            height: targetHeight,
            scaleFactor: scale
          }
        }
      };

    } finally {
      // Cleanup
      await fs.unlink(tempInput).catch(() => {});
      await fs.unlink(tempOutput).catch(() => {});
    }
  }

  runPythonRemoveBg(input, output) {
    return new Promise((resolve, reject) => {
      const py = spawn(this.pythonPath, [this.scriptPath, input, output]);
      py.stderr.on('data', (data) => console.error(`Python: ${data}`));
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
