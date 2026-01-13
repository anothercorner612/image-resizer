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
    this.scriptPath = path.join(__dirname, 'remove_bg.py');
  }

  async process(inputBuffer) {
    const tempInput = path.join(__dirname, `temp_in_${Date.now()}.png`);
    const tempOutput = path.join(__dirname, `temp_out_${Date.now()}.png`);

    try {
      await fs.writeFile(tempInput, inputBuffer);
      await this.runPythonRemoveBg(tempInput, tempOutput);

      let processedImage = sharp(tempOutput);
      const trimmedBuffer = await processedImage.trim().toBuffer();
      const metadata = await sharp(trimmedBuffer).metadata();

      const canvasWidth = 2000;
      const canvasHeight = 2500;
      
      const targetHeight = Math.round(canvasHeight * 0.8);
      const scale = targetHeight / metadata.height;
      const targetWidth = Math.round(metadata.width * scale);

      const resizedProduct = await sharp(trimmedBuffer)
        .resize(targetWidth, targetHeight)
        .toBuffer();

      return await sharp({
        create: {
          width: canvasWidth,
          height: canvasHeight,
          channels: 4,
          background: '#f2f2f2'
        }
      })
      .composite([{
        input: resizedProduct,
        gravity: 'center'
      }])
      .png()
      .toBuffer();

    } finally {
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
