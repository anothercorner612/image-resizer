import sharp from 'sharp';
import { ProductScaler } from './scaler.js';
import fs from 'fs/promises';
import { removeBackground as removeBackgroundAI } from '@imgly/background-removal-node';

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

      // 4. Prepare product image (with or without background removal)
      console.log('Preparing product image...');
      let processedProduct;

      if (this.enableBackgroundRemoval && !metadata.hasAlpha) {
        console.log('⚠️  Note: Basic background cleanup applied (Sharp has limited background removal)');
        processedProduct = await this.cleanupBackground(workingBuffer);
      } else {
        // Use image as-is, just ensure alpha channel
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

      // 7. Generate contact shadow
      console.log('Generating contact shadow...');
      const shadowBuffer = await this.createContactShadow(
        scalingInfo.scaled.width,
        scalingInfo.scaled.height
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
   * Auto-trim black bars and letterboxing from images
   * Removes solid black or white borders before processing
   * More conservative to avoid removing actual product content
   * @param {Buffer} buffer - Input image buffer
   * @returns {Promise<Buffer>} Trimmed image buffer
   */
  async autoTrim(buffer) {
    try {
      const image = sharp(buffer);
      const metadata = await image.metadata();

      // Try trimming with threshold for black borders only
      // Use lower threshold (2 instead of 10) to be more conservative
      // Only trim if it's truly solid black/white
      let trimmedBuffer = await image
        .trim({
          threshold: 2, // Very conservative - only pure black/white
          background: { r: 0, g: 0, b: 0 } // Trim black
        })
        .toBuffer();

      // Check if trimming actually removed significant borders
      // Require at least 50px removed to prevent accidental trimming of content
      const trimmedMetadata = await sharp(trimmedBuffer).metadata();
      const trimmedSignificantly = (
        (metadata.width - trimmedMetadata.width) > 50 ||
        (metadata.height - trimmedMetadata.height) > 50
      );

      if (trimmedSignificantly) {
        console.log(`✓ Trimmed black bars: ${metadata.width}×${metadata.height} → ${trimmedMetadata.width}×${trimmedMetadata.height}`);
        buffer = trimmedBuffer;
      } else {
        console.log('No significant black borders detected');
      }

      // Also try trimming white borders (only if significant)
      const currentMetadata = await sharp(buffer).metadata();
      trimmedBuffer = await sharp(buffer)
        .trim({
          threshold: 2,
          background: { r: 255, g: 255, b: 255 } // Trim white
        })
        .toBuffer();

      // Check if white trimming removed something significant
      const whiteMetadata = await sharp(trimmedBuffer).metadata();
      const whiteTrimmedSignificantly = (
        (currentMetadata.width - whiteMetadata.width) > 50 ||
        (currentMetadata.height - whiteMetadata.height) > 50
      );

      if (whiteTrimmedSignificantly) {
        console.log(`✓ Trimmed white borders: ${currentMetadata.width}×${currentMetadata.height} → ${whiteMetadata.width}×${whiteMetadata.height}`);
        buffer = trimmedBuffer;
      } else {
        console.log('No significant white borders detected');
      }

      return buffer;

    } catch (error) {
      console.warn('Auto-trim failed, using original image:', error.message);
      // Return original if trimming fails
      return buffer;
    }
  }

  /**
   * Remove background using AI model
   * Uses @imgly/background-removal-node for high-quality background removal
   * @param {Buffer} buffer - Input image buffer
   * @returns {Promise<Buffer>} Image with background removed (PNG with alpha)
   */
  async cleanupBackground(buffer) {
    try {
      console.log('Removing background with AI model...');

      // Use AI model to remove background
      // First run will download ~50MB model (cached for future use)
      const blob = await removeBackgroundAI(buffer);

      // Convert Blob to Buffer
      const arrayBuffer = await blob.arrayBuffer();
      const resultBuffer = Buffer.from(arrayBuffer);

      console.log('✓ Background removed successfully');
      return resultBuffer;

    } catch (error) {
      console.error('AI background removal failed:', error.message);
      console.log('Falling back to basic cleanup...');

      // Fallback to basic cleanup if AI fails
      try {
        const image = sharp(buffer);
        return await image
          .ensureAlpha()
          .trim()
          .toBuffer();
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError.message);
        // Return original if everything fails
        return buffer;
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
   * @returns {Promise<Buffer>} Shadow buffer
   */
  async createContactShadow(productWidth, productHeight) {
    const shadowPos = this.scaler.getShadowPosition(productWidth, productHeight);

    // Create SVG for elliptical shadow with blur
    const svg = `
      <svg width="${productWidth}" height="${productHeight}">
        <defs>
          <filter id="blur">
            <feGaussianBlur in="SourceGraphic" stdDeviation="15" />
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
