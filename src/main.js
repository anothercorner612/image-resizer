import dotenv from 'dotenv';
import { ShopifyClient } from './shopify.js';
import { MetafieldManager } from './metafields.js';
import { ImageProcessor } from './imageProcessor.js';
import { ProductScaler } from './scaler.js';

// Load environment variables
dotenv.config();

/**
 * Main Shopify Image Automation Orchestrator
 */
export class ShopifyImageAutomation {
  constructor(config = {}) {
    // Load configuration from environment or passed config
    this.config = {
      storeUrl: config.storeUrl || process.env.SHOPIFY_STORE_URL,
      accessToken: config.accessToken || process.env.SHOPIFY_ACCESS_TOKEN,
      canvasWidth: config.canvasWidth || process.env.CANVAS_WIDTH || 2000,
      canvasHeight: config.canvasHeight || process.env.CANVAS_HEIGHT || 2500,
      backgroundColor: config.backgroundColor || process.env.BACKGROUND_COLOR || '#f3f3f4',
      shadowOpacity: config.shadowOpacity || process.env.SHADOW_OPACITY || 0.18,
      webpQuality: config.webpQuality || process.env.WEBP_QUALITY || 90,
      dryRun: config.dryRun !== undefined ? config.dryRun : process.env.DRY_RUN === 'true',
      maxConcurrent: config.maxConcurrent || process.env.MAX_CONCURRENT_PROCESSES || 5,
      enableAutoTrim: config.enableAutoTrim !== undefined ? config.enableAutoTrim : process.env.ENABLE_AUTO_TRIM !== 'false',
      enableBackgroundRemoval: config.enableBackgroundRemoval !== undefined ? config.enableBackgroundRemoval : process.env.ENABLE_BACKGROUND_REMOVAL === 'true',
    };

    // Validate configuration
    this.validateConfig();

    // Initialize components
    this.shopify = new ShopifyClient({
      storeUrl: this.config.storeUrl,
      accessToken: this.config.accessToken,
    });

    this.metafields = new MetafieldManager(this.shopify);
    this.imageProcessor = new ImageProcessor(this.config);

    console.log('=== Shopify Image Automation ===');
    console.log(`Store: ${this.config.storeUrl}`);
    console.log(`Canvas: ${this.config.canvasWidth}×${this.config.canvasHeight}`);
    console.log(`Background: ${this.config.backgroundColor}`);
    console.log(`Shadow Opacity: ${this.config.shadowOpacity}`);
    console.log(`Dry Run: ${this.config.dryRun ? 'YES' : 'NO'}`);
    console.log(`Auto-Trim: ${this.config.enableAutoTrim ? 'ENABLED' : 'DISABLED'}`);
    console.log(`Background Removal: ${this.config.enableBackgroundRemoval ? 'ENABLED' : 'DISABLED'}`);
    console.log('================================\n');
  }

  /**
   * Validate configuration
   */
  validateConfig() {
    if (!this.config.storeUrl) {
      throw new Error('SHOPIFY_STORE_URL is required');
    }
    if (!this.config.accessToken) {
      throw new Error('SHOPIFY_ACCESS_TOKEN is required');
    }
  }

  /**
   * Main entry point - run the automation
   * @param {Object} options - Runtime options
   */
  async run(options = {}) {
    try {
      const startTime = Date.now();

      // Get limit from options or command line
      const limit = options.limit || this.getCommandLineLimit();

      console.log('🚀 Starting automation...\n');

      // 1. Fetch all products
      console.log('📦 Fetching products from Shopify...');
      let allProducts = await this.shopify.getAllProducts();

      if (limit) {
        console.log(`⚠️  Limiting to ${limit} products`);
        allProducts = allProducts.slice(0, limit);
      }

      console.log(`Found ${allProducts.length} products\n`);

      // 2. Filter products that need harmonization
      const productsToProcess = await this.metafields.getProductsNeedingHarmonization(allProducts);

      if (productsToProcess.length === 0) {
        console.log('✨ All products are already harmonized!');
        return;
      }

      console.log(`\n📋 ${productsToProcess.length} products need harmonization\n`);

      // 3. Process products in batches
      await this.processBatch(productsToProcess);

      // 4. Show statistics
      const stats = await this.metafields.getStatistics(allProducts);
      this.printStatistics(stats);

      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      console.log(`\n✓ Automation completed in ${duration}s`);

    } catch (error) {
      console.error('\n❌ Automation failed:', error.message);
      throw error;
    }
  }

  /**
   * Process a batch of products with concurrency control
   * @param {Array} products - Products to process
   */
  async processBatch(products) {
    const maxConcurrent = parseInt(this.config.maxConcurrent);
    let completed = 0;
    let failed = 0;

    console.log(`Processing ${products.length} products (max ${maxConcurrent} concurrent)...\n`);

    // Process in chunks
    for (let i = 0; i < products.length; i += maxConcurrent) {
      const chunk = products.slice(i, i + maxConcurrent);
      const promises = chunk.map(product => this.processProduct(product));

      const results = await Promise.allSettled(promises);

      // Count results
      results.forEach(result => {
        if (result.status === 'fulfilled') {
          completed++;
        } else {
          failed++;
        }
      });

      console.log(`Progress: ${completed + failed}/${products.length} (✓ ${completed}, ✗ ${failed})\n`);

      // Rate limiting delay between chunks
      if (i + maxConcurrent < products.length) {
        await this.delay(1000);
      }
    }

    console.log(`\n📊 Batch complete: ${completed} succeeded, ${failed} failed`);
  }

  /**
   * Process a single product
   * @param {Object} product - Product to process
   */
  async processProduct(product) {
    const productId = product.id;
    const productTitle = product.title;

    try {
      console.log(`\n${'='.repeat(60)}`);
      console.log(`Processing: ${productTitle} (ID: ${productId})`);
      console.log('='.repeat(60));

      // Mark as in progress
      await this.metafields.markAsInProgress(productId, { productTitle });

      // Get product images
      const images = product.images || [];

      if (images.length === 0) {
        console.log('⚠️  No images found, skipping...');
        await this.metafields.markAsHarmonized(productId, {
          productTitle,
          processedImages: [],
          category: 'no_images'
        });
        return;
      }

      console.log(`Found ${images.length} image(s)`);

      const processedImages = [];

      // Process each image
      for (let i = 0; i < images.length; i++) {
        const image = images[i];
        console.log(`\nProcessing image ${i + 1}/${images.length}...`);
        console.log(`URL: ${image.src}`);

        try {
          // Download image
          console.log('Downloading image...');
          const imageBuffer = await this.shopify.downloadImage(image.src);

          // Process image
          const result = await this.imageProcessor.processImage(imageBuffer, {
            title: product.title,
            type: product.product_type
          });

          // Upload or save based on dry run mode
          if (this.config.dryRun) {
            console.log('🔍 DRY RUN - Would upload processed image');
          } else {
            console.log('Uploading processed image to Shopify...');

            // Convert buffer to base64 for upload
            const base64Image = result.buffer.toString('base64');

            // Upload as new image
            const uploadedImage = await this.shopify.uploadProductImage(productId, {
              attachment: base64Image,
              filename: `${product.handle}-harmonized-${i + 1}.webp`
            });

            // Delete old image
            await this.shopify.deleteProductImage(productId, image.id);

            console.log('✓ Image uploaded and old image removed');
          }

          processedImages.push({
            originalId: image.id,
            category: result.scalingInfo.category,
            dimensions: result.scalingInfo.scaled,
            processedAt: new Date().toISOString()
          });

        } catch (error) {
          console.error(`Error processing image ${i + 1}:`, error.message);
          // Continue with next image
        }
      }

      // Mark as harmonized
      await this.metafields.markAsHarmonized(productId, {
        productTitle,
        processedImages,
        category: processedImages[0]?.category || 'unknown',
        scaledDimensions: processedImages[0]?.dimensions || {}
      });

      console.log(`\n✓ Product ${productTitle} completed`);

    } catch (error) {
      console.error(`\n✗ Failed to process product ${productTitle}:`, error.message);
      await this.metafields.markAsFailed(productId, error, { productTitle });
      throw error;
    }
  }

  /**
   * Print statistics
   * @param {Object} stats - Statistics object
   */
  printStatistics(stats) {
    console.log('\n' + '='.repeat(60));
    console.log('📊 HARMONIZATION STATISTICS');
    console.log('='.repeat(60));
    console.log(`Total Products:     ${stats.total}`);
    console.log(`✓ Completed:        ${stats.completed} (${this.percentage(stats.completed, stats.total)}%)`);
    console.log(`→ In Progress:      ${stats.inProgress}`);
    console.log(`✗ Failed:           ${stats.failed}`);
    console.log(`⊘ Skipped:          ${stats.skipped}`);
    console.log(`⏳ Pending:         ${stats.pending}`);
    console.log('='.repeat(60));
  }

  /**
   * Calculate percentage
   * @param {number} value - Value
   * @param {number} total - Total
   * @returns {string} Percentage string
   */
  percentage(value, total) {
    if (total === 0) return '0.0';
    return ((value / total) * 100).toFixed(1);
  }

  /**
   * Get limit from command line arguments
   * @returns {number|null} Limit or null
   */
  getCommandLineLimit() {
    const args = process.argv.slice(2);
    const limitIndex = args.findIndex(arg => arg === '--limit' || arg === '-l');
    if (limitIndex !== -1 && args[limitIndex + 1]) {
      return parseInt(args[limitIndex + 1]);
    }
    return null;
  }

  /**
   * Delay helper
   * @param {number} ms - Milliseconds to delay
   * @returns {Promise}
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const automation = new ShopifyImageAutomation();
  automation.run().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}
