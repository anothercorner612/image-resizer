/**
 * Product Scaler - Handles categorization and scaling logic
 * Implements conditional scaling rules based on product dimensions and type
 */
export class ProductScaler {
  constructor(canvasWidth, canvasHeight) {
    this.canvasWidth = canvasWidth;
    this.canvasHeight = canvasHeight;

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
        // 82% of longest side
        const longestSide = Math.max(width, height);
        const scaleFactor = (this.canvasHeight * 0.82) / longestSide;
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
      scaleFactor: scaledWidth / width
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
   * @returns {Object} Shadow dimensions and position
   */
  getShadowPosition(scaledWidth, scaledHeight) {
    const centerPos = this.getCenterPosition(scaledWidth, scaledHeight);

    // Shadow ellipse dimensions (proportional to product width)
    const shadowWidth = Math.round(scaledWidth * 0.8);
    const shadowHeight = Math.round(scaledWidth * 0.15);

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
    console.log(`Canvas: ${scalingInfo.canvas.width}×${scalingInfo.canvas.height}`);
    console.log(`Aspect Ratio: ${scalingInfo.aspectRatio}`);
    console.log('-------------------------\n');
  }
}
