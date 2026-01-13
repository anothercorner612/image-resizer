/**
 * Product Scaler - Handles categorization and scaling logic
 * Implements conditional scaling rules based on product dimensions and type
 */
export class ProductScaler {
  constructor(canvasWidth, canvasHeight) {
    this.canvasWidth = canvasWidth;
    this.canvasHeight = canvasHeight;

    // Maximum scale factor to prevent blurry upscaling (150%)
    this.maxScaleFactor = 1.5;

    // Keywords for small/accessory detection
    this.smallAccessoryKeywords = [
      'pin',
      'badge',
      'sticker',
      'card',
      'bookmark',
      'keychain',
      'magnet',
      'patch',
      'button'
    ];
  }

  /**
   * Categorize a product based on dimensions and metadata
   * @param {number} width - Original image width
   * @param {number} height - Original image height
   * @param {string} title - Product title
   * @param {string} type - Product type
   * @returns {Object} Category and reason
   */
  categorizeProduct(width, height, title = '', type = '') {
    const aspectRatio = width / height;
    const longestSide = Math.max(width, height);
    const searchText = `${title} ${type}`.toLowerCase();

    // Check for small/accessory based on keywords
    const hasSmallKeyword = this.smallAccessoryKeywords.some(keyword =>
      searchText.includes(keyword)
    );

    // Apply categorization rules in priority order
    if (longestSide < 500 || hasSmallKeyword) {
      return {
        category: 'small_accessory',
        reason: longestSide < 500
          ? `Longest side (${longestSide}px) < 500px`
          : `Contains keyword: ${this.smallAccessoryKeywords.find(k => searchText.includes(k))}`
      };
    }

    if (aspectRatio < 0.5) {
      return {
        category: 'tall_thin',
        reason: `Aspect ratio ${aspectRatio.toFixed(2)} < 0.5 (height > 2× width)`
      };
    }

    if (aspectRatio > 1.5) {
      return {
        category: 'wide',
        reason: `Aspect ratio ${aspectRatio.toFixed(2)} > 1.5 (width > 1.5× height)`
      };
    }

    return {
      category: 'default',
      reason: `Standard aspect ratio ${aspectRatio.toFixed(2)}`
    };
  }

  /**
   * Calculate scaled dimensions based on category
   * @param {number} width - Original image width
   * @param {number} height - Original image height
   * @param {string} category - Product category
   * @returns {Object} Scaled width and height
   */
  calculateScaledDimensions(width, height, category) {
    const aspectRatio = width / height;
    let scaledWidth, scaledHeight;

    switch (category) {
      case 'tall_thin':
        // 85% of canvas height
        scaledHeight = Math.round(this.canvasHeight * 0.85);
        scaledWidth = Math.round(scaledHeight * aspectRatio);
        break;

      case 'wide':
        // 82% of canvas width
        scaledWidth = Math.round(this.canvasWidth * 0.82);
        scaledHeight = Math.round(scaledWidth / aspectRatio);
        break;

      case 'small_accessory':
        // 50% of canvas height
        scaledHeight = Math.round(this.canvasHeight * 0.50);
        scaledWidth = Math.round(scaledHeight * aspectRatio);
        break;

      case 'default':
      default:
        // 82% of longest side, but cap at 150% maximum scale factor
        const longestSide = Math.max(width, height);
        let scaleFactor = (this.canvasHeight * 0.82) / longestSide;

        // Cap scale factor at 150% to prevent blurry upscaling
        if (scaleFactor > this.maxScaleFactor) {
          console.log(`⚠️  Capping scale factor at ${this.maxScaleFactor * 100}% (would have been ${(scaleFactor * 100).toFixed(1)}%)`);
          scaleFactor = this.maxScaleFactor;
        }

        scaledWidth = Math.round(width * scaleFactor);
        scaledHeight = Math.round(height * scaleFactor);
        break;
    }

    // Ensure scaled dimensions fit within canvas
    if (scaledWidth > this.canvasWidth) {
      const ratio = this.canvasWidth / scaledWidth;
      scaledWidth = this.canvasWidth;
      scaledHeight = Math.round(scaledHeight * ratio);
    }

    if (scaledHeight > this.canvasHeight) {
      const ratio = this.canvasHeight / scaledHeight;
      scaledHeight = this.canvasHeight;
      scaledWidth = Math.round(scaledWidth * ratio);
    }

    return {
      width: scaledWidth,
      height: scaledHeight,
      scaleFactor: scaledWidth / width,
      cappedAt150: category === 'default' && (scaledWidth / width) >= this.maxScaleFactor
    };
  }

  /**
   * Get complete scaling information for a product
   * @param {number} width - Original image width
   * @param {number} height - Original image height
   * @param {string} title - Product title
   * @param {string} type - Product type
   * @returns {Object} Complete scaling info
   */
  getScalingInfo(width, height, title = '', type = '') {
    const { category, reason } = this.categorizeProduct(width, height, title, type);
    const scaledDimensions = this.calculateScaledDimensions(width, height, category);

    return {
      original: { width, height },
      category,
      reason,
      scaled: scaledDimensions,
      canvas: {
        width: this.canvasWidth,
        height: this.canvasHeight
      },
      aspectRatio: (width / height).toFixed(3)
    };
  }

  /**
   * Get positioning coordinates to center the product on canvas
   * @param {number} scaledWidth - Scaled product width
   * @param {number} scaledHeight - Scaled product height
   * @returns {Object} X and Y coordinates
   */
  getCenterPosition(scaledWidth, scaledHeight) {
    return {
      x: Math.round((this.canvasWidth - scaledWidth) / 2),
      y: Math.round((this.canvasHeight - scaledHeight) / 2)
    };
  }

  /**
   * Get shadow positioning (at base of product)
   * @param {number} scaledWidth - Scaled product width
   * @param {number} scaledHeight - Scaled product height
   * @param {string} category - Product category
   * @returns {Object} Shadow dimensions and position
   */
  getShadowPosition(scaledWidth, scaledHeight, category = 'default') {
    const centerPos = this.getCenterPosition(scaledWidth, scaledHeight);
    const aspectRatio = scaledWidth / scaledHeight;

    // Calculate shadow dimensions based on product category and shape
    let shadowWidth, shadowHeight;

    if (category === 'tall_thin' || aspectRatio < 0.5) {
      // For tall/thin products (bottles, vases, etc.)
      // Shadow should be wider than the product base for realism
      shadowWidth = Math.round(scaledWidth * 1.4); // 140% of product width
      shadowHeight = Math.round(shadowWidth * 0.15); // Shallow ellipse
    } else if (category === 'wide' || aspectRatio > 1.5) {
      // For wide products
      shadowWidth = Math.round(scaledWidth * 0.85);
      shadowHeight = Math.round(shadowWidth * 0.12); // Very shallow
    } else if (category === 'small_accessory') {
      // For small items
      shadowWidth = Math.round(scaledWidth * 0.9);
      shadowHeight = Math.round(shadowWidth * 0.18); // Slightly taller
    } else {
      // Default products - use average of width/height for more natural shadow
      const baseDimension = Math.max(scaledWidth * 0.7, Math.min(scaledWidth, scaledHeight));
      shadowWidth = Math.round(baseDimension * 0.85);
      shadowHeight = Math.round(baseDimension * 0.15);
    }

    // Ensure shadow isn't too small
    shadowWidth = Math.max(shadowWidth, 100);
    shadowHeight = Math.max(shadowHeight, 15);

    // Position shadow at the base of the product
    const shadowX = Math.round((this.canvasWidth - shadowWidth) / 2);
    const shadowY = centerPos.y + scaledHeight - Math.round(shadowHeight / 2);

    return {
      width: shadowWidth,
      height: shadowHeight,
      x: shadowX,
      y: shadowY,
      rx: Math.round(shadowWidth / 2),
      ry: Math.round(shadowHeight / 2)
    };
  }

  /**
   * Log scaling information
   * @param {Object} scalingInfo - Scaling information object
   */
  logScalingInfo(scalingInfo) {
    console.log('\n--- Scaling Information ---');
    console.log(`Category: ${scalingInfo.category}`);
    console.log(`Reason: ${scalingInfo.reason}`);
    console.log(`Original: ${scalingInfo.original.width}×${scalingInfo.original.height}`);
    console.log(`Scaled: ${scalingInfo.scaled.width}×${scalingInfo.scaled.height}`);
    console.log(`Scale Factor: ${(scalingInfo.scaled.scaleFactor * 100).toFixed(1)}%`);
    if (scalingInfo.scaled.cappedAt150) {
      console.log('⚠️  Scale capped at 150% to prevent blurry upscaling');
    }
    console.log(`Canvas: ${scalingInfo.canvas.width}×${scalingInfo.canvas.height}`);
    console.log(`Aspect Ratio: ${scalingInfo.aspectRatio}`);
    console.log('-------------------------\n');
  }
}
