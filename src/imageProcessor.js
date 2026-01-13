import sharp from 'sharp';
import { ProductScaler } from './scaler.js';
import fs from 'fs/promises';
import { createRequire } from 'module';

// free-background-remover is CommonJS, need to use require
const require = createRequire(import.meta.url);
const BGRMPipeline = require('free-background-remover');

/**
 * Image Processor - Handles all image processing operations
 * Uses Sharp library for image manipulation
 */
export class ImageProcessor {
  constructor(config) {
    this.canvasWidth = parseInt(config.canvasWidth) || 2000;
    this.canvasHeight = parseInt(config.canvasHeight) || 2500;
    this.backgroundColor = config.backgroundColor || '#f3f3f4';
    this.shadowOpacity = parseFloat(config.shadowOpacity) || 0.18;
    this.webpQuality = parseInt(config.webpQuality) || 90;

    // Optional features (can be disabled via config)
    this.enableAutoTrim = config.enableAutoTrim !== false; // default: true
    this.enableBackgroundRemoval = config.enableBackgroundRemoval !== false; // default: true

    this.scaler = new ProductScaler(this.canvasWidth, this.canvasHeight);

    // Initialize background removal pipeline (reuse for batch processing)
    if (this.enableBackgroundRemoval) {
      console.log('Initializing AI background removal pipeline...');
      this.bgRemovalPipeline = new BGRMPipeline({
        onnxModelProfile: BGRMPipeline.ONNX_MODEL_PROFILE.U2NET,
        dither: BGRMPipeline.NATIVE_DITHER
      });
      console.log('✓ Background removal ready (using U2Net model)');
    }
  }

  /**
   * Process an image buffer
   * @param {Buffer} buffer - Input image buffer
   * @param {Object} productInfo - Product information (title, type)
   * @returns {Promise<Object>} Processed image buffer and metadata
   */
  async processImage(buffer, productInfo = {}) {
    try {
      console.log('\n=== Processing Image ===');

      let workingBuffer = buffer;

      // 1. Auto-trim black bars and letterboxing (optional)
      if (this.enableAutoTrim) {
        console.log('Auto-trimming letterboxing/black bars...');
        workingBuffer = await this.autoTrim(workingBuffer);
      } else {
        console.log('Auto-trim disabled, using original image');
      }

      // 2. Load image and get metadata
      const image = sharp(workingBuffer);
      const metadata = await image.metadata();
      console.log(`Original dimensions: ${metadata.width}×${metadata.height}`);

      // 3. Get scaling information
      const scalingInfo = this.scaler.getScalingInfo(
        metadata.width,
        metadata.height,
        productInfo.title || '',
        productInfo.type || ''
      );
      this.scaler.logScalingInfo(scalingInfo);

      // 4. Remove background with AI (if enabled)
      console.log('Preparing product image...');
      let processedProduct;

      if (this.enableBackgroundRemoval) {
        // Always run AI background removal if enabled
        // Product photos often have alpha channels but still have white backgrounds
        processedProduct = await this.cleanupBackground(workingBuffer);
      } else {
        // Use image as-is, just ensure alpha channel
        console.log('Background removal disabled, using original image');
        processedProduct = await sharp(workingBuffer).ensureAlpha().toBuffer();
      }

      // 5. Resize
      const resizedProduct = await sharp(processedProduct)
        .resize(scalingInfo.scaled.width, scalingInfo.scaled.height, {
          fit: 'contain',
          background: { r: 0, g: 0, b: 0, alpha: 0 }
        })
        .toBuffer();

      // 6. Create canvas with background color
      console.log('Creating canvas with background...');
      const canvas = await this.createCanvas();

      // 7. Generate contact shadow (category-aware)
      console.log('Generating contact shadow...');
      const shadowBuffer = await this.createContactShadow(
        scalingInfo.scaled.width,
        scalingInfo.scaled.height,
        scalingInfo.category
      );

      // 8. Get positioning
      const centerPos = this.scaler.getCenterPosition(
        scalingInfo.scaled.width,
        scalingInfo.scaled.height
      );

      // 9. Composite everything together
      console.log('Compositing layers...');
      const finalImage = await sharp(canvas)
        .composite([
          // First: shadow layer
          {
            input: shadowBuffer,
            top: centerPos.y,
            left: centerPos.x,
            blend: 'over'
          },
          // Second: product layer (on top of shadow)
          {
            input: resizedProduct,
            top: centerPos.y,
            left: centerPos.x,
            blend: 'over'
          }
        ])
        .webp({ quality: this.webpQuality })
        .toBuffer();

      console.log('✓ Image processing complete');

      return {
        buffer: finalImage,
        scalingInfo,
        metadata: {
          width: this.canvasWidth,
          height: this.canvasHeight,
          format: 'webp',
          size: finalImage.length
        }
      };

    } catch (error) {
      console.error('Error processing image:', error.message);
      throw error;
    }
  }

  /**
   * Auto-trim letterboxing and solid borders
   * Removes black bars and solid white/light borders
   * @param {Buffer} buffer - Input image buffer
   * @returns {Promise<Buffer>} Trimmed image buffer
   */
  async autoTrim(buffer) {
    try {
      const image = sharp(buffer);
      const metadata = await image.metadata();
      let didTrim = false;

      // Try trimming solid black borders (letterboxing)
      // Use threshold 5 to handle JPEG artifacts
      try {
        const trimmedBuffer = await sharp(buffer)
          .trim({
            threshold: 5,
            background: { r: 0, g: 0, b: 0 }
          })
          .toBuffer();

        const trimmedMeta = await sharp(trimmedBuffer).metadata();
        const removed = Math.max(
          metadata.width - trimmedMeta.width,
          metadata.height - trimmedMeta.height
        );

        if (removed > 20) {
          console.log(`✓ Trimmed black letterboxing: ${metadata.width}×${metadata.height} → ${trimmedMeta.width}×${trimmedMeta.height}`);
          buffer = trimmedBuffer;
          didTrim = true;
        }
      } catch (e) {
        // Trim failed, continue
      }

      if (!didTrim) {
        console.log('No letterboxing detected');
      }

      return buffer;

    } catch (error) {
      console.warn('Auto-trim failed, using original image:', error.message);
      return buffer;
    }
  }

  /**
   * Remove background using local AI (U2Net model via free-background-remover)
   * High-quality AI-powered background removal with no API costs
   * @param {Buffer} buffer - Input image buffer
   * @returns {Promise<Buffer>} Image with background removed (PNG with alpha)
   */
  async cleanupBackground(buffer) {
    if (!this.bgRemovalPipeline) {
      console.log('Background removal disabled, using original image');
      return await sharp(buffer).ensureAlpha().toBuffer();
    }

    try {
      console.log('Removing background with local AI (U2Net)...');

      // Create temp directory if it doesn't exist
      const tempDir = './temp';
      try {
        await fs.mkdir(tempDir, { recursive: true });
      } catch (e) {
        // Directory exists, continue
      }

      // Generate unique temp filenames
      const timestamp = Date.now();
      const tempInput = `${tempDir}/input_${timestamp}.png`;
      const tempOutput = `${tempDir}/output_${timestamp}.png`;

      try {
        // Save buffer to temp file
        await fs.writeFile(tempInput, buffer);

        // Process with free-background-remover
        // Note: run() processes a single file and returns when complete
        await this.bgRemovalPipeline.run(tempInput, tempOutput);

        // Read result
        const resultBuffer = await fs.readFile(tempOutput);
        console.log('✓ Background removed successfully with local AI');

        return resultBuffer;

      } finally {
        // Clean up temp files
        try {
          await fs.unlink(tempInput).catch(() => {});
          await fs.unlink(tempOutput).catch(() => {});
        } catch (cleanupError) {
          // Ignore cleanup errors
        }
      }

    } catch (error) {
      console.warn('Local AI background removal failed, falling back to basic processing:', error.message);

      // Fallback: Basic Sharp processing
      try {
        const image = sharp(buffer);
        const metadata = await image.metadata();

        // If image already has transparency, just trim edges
        if (metadata.hasAlpha) {
          console.log('Image already has alpha channel, trimming edges');
          return await sharp(buffer)
            .trim({ threshold: 5 })
            .ensureAlpha()
            .toBuffer();
        }

        // Otherwise, add alpha channel and trim
        console.log('Adding alpha channel');
        return await sharp(buffer)
          .ensureAlpha()
          .trim({ threshold: 10 })
          .toBuffer();

      } catch (fallbackError) {
        console.warn('Basic processing failed:', fallbackError.message);
        // Last resort: return original with alpha
        try {
          return await sharp(buffer).ensureAlpha().toBuffer();
        } catch (lastError) {
          console.error('Complete fallback failed:', lastError.message);
          return buffer;
        }
      }
    }
  }

  /**
   * Legacy function - kept for compatibility
   * @deprecated Use cleanupBackground instead
   * @param {Buffer} buffer - Input image buffer
   * @returns {Promise<Buffer>} Image buffer
   */
  async removeBackground(buffer) {
    return this.cleanupBackground(buffer);
  }

  /**
   * Create a canvas with background color
   * @returns {Promise<Buffer>} Canvas buffer
   */
  async createCanvas() {
    // Parse hex color to RGB
    const rgb = this.hexToRgb(this.backgroundColor);

    return await sharp({
      create: {
        width: this.canvasWidth,
        height: this.canvasHeight,
        channels: 4,
        background: { r: rgb.r, g: rgb.g, b: rgb.b, alpha: 1 }
      }
    })
    .png()
    .toBuffer();
  }

  /**
   * Create contact shadow at product base
   * @param {number} productWidth - Scaled product width
   * @param {number} productHeight - Scaled product height
   * @param {string} category - Product category for shadow sizing
   * @returns {Promise<Buffer>} Shadow buffer
   */
  async createContactShadow(productWidth, productHeight, category = 'default') {
    const shadowPos = this.scaler.getShadowPosition(productWidth, productHeight, category);

    // Adjust blur based on shadow size for realism
    // Larger shadows need more blur to look natural
    const blurAmount = Math.max(12, Math.min(25, shadowPos.width * 0.015));

    // Create SVG for elliptical shadow with blur
    const svg = `
      <svg width="${productWidth}" height="${productHeight}">
        <defs>
          <filter id="blur">
            <feGaussianBlur in="SourceGraphic" stdDeviation="${blurAmount}" />
          </filter>
        </defs>
        <ellipse
          cx="${productWidth / 2}"
          cy="${productHeight - shadowPos.ry}"
          rx="${shadowPos.rx}"
          ry="${shadowPos.ry}"
          fill="rgba(0, 0, 0, ${this.shadowOpacity})"
          filter="url(#blur)"
        />
      </svg>
    `;

    return await sharp(Buffer.from(svg))
      .png()
      .toBuffer();
  }

  /**
   * Process and save image locally (for testing)
   * @param {string} inputPath - Input file path
   * @param {string} outputPath - Output file path
   * @param {Object} productInfo - Product information
   * @returns {Promise<Object>} Processing result
   */
  async processAndSave(inputPath, outputPath, productInfo = {}) {
    try {
      console.log(`\nProcessing: ${inputPath}`);

      // Read input file
      const buffer = await fs.readFile(inputPath);

      // Process image
      const result = await this.processImage(buffer, productInfo);

      // Save output file
      await fs.writeFile(outputPath, result.buffer);
      console.log(`✓ Saved to: ${outputPath}`);

      return {
        ...result,
        inputPath,
        outputPath
      };

    } catch (error) {
      console.error(`Error processing ${inputPath}:`, error.message);
      throw error;
    }
  }

  /**
   * Convert hex color to RGB
   * @param {string} hex - Hex color code
   * @returns {Object} RGB values
   */
  hexToRgb(hex) {
    // Remove # if present
    hex = hex.replace(/^#/, '');

    // Parse hex values
    const bigint = parseInt(hex, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;

    return { r, g, b };
  }

  /**
   * Get image dimensions from buffer
   * @param {Buffer} buffer - Image buffer
   * @returns {Promise<Object>} Width and height
   */
  async getImageDimensions(buffer) {
    const metadata = await sharp(buffer).metadata();
    return {
      width: metadata.width,
      height: metadata.height
    };
  }

  /**
   * Validate image format
   * @param {Buffer} buffer - Image buffer
   * @returns {Promise<boolean>} True if valid image
   */
  async isValidImage(buffer) {
    try {
      await sharp(buffer).metadata();
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Convert image to WebP format
   * @param {Buffer} buffer - Input image buffer
   * @returns {Promise<Buffer>} WebP buffer
   */
  async convertToWebP(buffer) {
    return await sharp(buffer)
      .webp({ quality: this.webpQuality })
      .toBuffer();
  }

  /**
   * Get image info for logging
   * @param {Buffer} buffer - Image buffer
   * @returns {Promise<Object>} Image information
   */
  async getImageInfo(buffer) {
    const metadata = await sharp(buffer).metadata();
    return {
      format: metadata.format,
      width: metadata.width,
      height: metadata.height,
      channels: metadata.channels,
      hasAlpha: metadata.hasAlpha,
      space: metadata.space,
      size: buffer.length
    };
  }
}
