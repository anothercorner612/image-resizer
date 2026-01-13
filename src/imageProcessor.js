const sharp = require('sharp');
const path = require('path');
const fs = require('fs').promises;
const { existsSync } = require('fs'); // Added for safety check
const { spawn } = require('child_process');

class ImageProcessor {
  constructor(config) {
    this.config = config;
    // We use 'python3' because your terminal says (venv) is active
    this.pythonPath = 'python3'; 
    
    // This is the fix: go UP from /src to the root to find the script
    this.scriptPath = path.join(__dirname, '..', 'remove_bg.py');

    console.log("--- DEBUG INFO ---");
    console.log(`Current Dir: ${__dirname}`);
    console.log(`Looking for Python Script at: ${this.scriptPath}`);
    
    if (existsSync(this.scriptPath)) {
      console.log("✅ Script found!");
    } else {
      console.log("❌ Script NOT found at that path.");
    }
  }

  async process(inputBuffer) {
    // Save temp files in the root to keep things simple
    const tempInput = path.join(__dirname, '..', `temp_in_${Date.now()}.png`);
    const tempOutput = path.join(__dirname, '..', `temp_out_${Date.now()}.png`);

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
      
      // Captures actual Python errors so we can see why it fails
      py.stderr.on('data', (data) => console.error(`Python Error: ${data}`));
      
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

module.exports = ImageProcessor;
