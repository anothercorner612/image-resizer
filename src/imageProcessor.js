const sharp = require('sharp');
const path = require('path');
const fs = require('fs').promises;
const { spawn } = require('child_process');

class ImageProcessor {
  constructor(config) {
    this.config = config;
    this.pythonPath = 'python3'; 
    
    // '..' moves UP from /src to the project root
    this.scriptPath = path.join(__dirname, '..', 'remove_bg.py');
    
    console.log("--- PATH CHECK ---");
    console.log(`Looking for script at: ${this.scriptPath}`);
  }

  /**
   * Main processing function
   */
  async process(inputBuffer) {
    const tempInput = path.join(__dirname, `temp_in_${Date.now()}.png`);
    const tempOutput = path.join(__dirname, `temp_out_${Date.now()}.png`);

    try {
      // 1. Save buffer to temp file for Python to read
      await fs.writeFile(tempInput, inputBuffer);

      // 2. Run Python background removal
      await this.runPythonRemoveBg(tempInput, tempOutput);

      // 3. Load the result from Python
      let processedImage = sharp(tempOutput);

      // 4. TRIM: This is crucial. It finds the actual edges of the product
      // that the Python script made solid.
      const trimmedBuffer = await processedImage.trim().toBuffer();
      const metadata = await sharp(trimmedBuffer).metadata();

      // 5. Create the 2000x2500 Canvas (Light Gray #f2f2f2)
      const canvasWidth = 2000;
      const canvasHeight = 2500;
      
      // Scale product to fit 80% of canvas height
      const targetHeight = Math.round(canvasHeight * 0.8);
      const scale = targetHeight / metadata.height;
      const targetWidth = Math.round(metadata.width * scale);

      const resizedProduct = await sharp(trimmedBuffer)
        .resize(targetWidth, targetHeight)
        .toBuffer();

      // 6. Create final composition
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
      // Cleanup temp files
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

  // --- HELPER FUNCTIONS REQUIRED BY INDEX.JS ---

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

module.exports = ImageProcessor;
