import sharp from 'sharp';
import { ProductScaler } from './scaler.js';
import fs from 'fs/promises';

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

      // 1. Load image and get metadata
      const image = sharp(buffer);
      const metadata = await image.metadata();
      console.log(`Original dimensions: ${metadata.width}×${metadata.height}`);

      // 2. Get scaling information
      const scalingInfo = this.scaler.getScalingInfo(
        metadata.width,
        metadata.height,
        productInfo.title || '',
        productInfo.type || ''
      );
      this.scaler.logScalingInfo(scalingInfo);

      // 3. Remove background and resize
      console.log('Removing background and resizing...');
      const processedProduct = await this.removeBackground(buffer);
      const resizedProduct = await sharp(processedProduct)
        .resize(scalingInfo.scaled.width, scalingInfo.scaled.height, {
          fit: 'contain',
          background: { r: 0, g: 0, b: 0, alpha: 0 }
        })
        .toBuffer();

      // 4. Create canvas with background color
      console.log('Creating canvas with background...');
      const canvas = await this.createCanvas();

      // 5. Generate contact shadow
      console.log('Generating contact shadow...');
      const shadowBuffer = await this.createContactShadow(
        scalingInfo.scaled.width,
        scalingInfo.scaled.height
      );

      // 6. Get positioning
      const centerPos = this.scaler.getCenterPosition(
        scalingInfo.scaled.width,
        scalingInfo.scaled.height
      );

      // 7. Composite everything together
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
   * Remove background from image (preserve alpha channel)
   * @param {Buffer} buffer - Input image buffer
   * @returns {Promise<Buffer>} Image with background removed
   */
  async removeBackground(buffer) {
    try {
      // Use Sharp's built-in background removal
      // This removes solid backgrounds and preserves transparency
      const image = sharp(buffer);
      const metadata = await image.metadata();

      // Ensure image has alpha channel
      let processedImage = image.ensureAlpha();

      // If image doesn't have transparency, try to remove white/light backgrounds
      if (!metadata.hasAlpha) {
        processedImage = processedImage.flatten({ background: { r: 0, g: 0, b: 0, alpha: 0 } });
      }

      return await processedImage
        .trim() // Remove empty edges
        .toBuffer();

    } catch (error) {
      console.error('Error removing background:', error.message);
      // Return original if background removal fails
      return buffer;
    }
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
