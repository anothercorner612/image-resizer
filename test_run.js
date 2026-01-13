import dotenv from 'dotenv';
import { ShopifyClient } from './src/shopify.js';
import { ImageProcessor } from './src/imageProcessor.js';
import { ProductScaler } from './src/scaler.js';
import fs from 'fs/promises';
import path from 'path';

// Load environment variables
dotenv.config();

/**
 * Test Runner - Finds examples of each category and generates comparison HTML
 */
class TestRunner {
  constructor() {
    this.config = {
      storeUrl: process.env.SHOPIFY_STORE_URL,
      accessToken: process.env.SHOPIFY_ACCESS_TOKEN,
      canvasWidth: process.env.CANVAS_WIDTH || 2000,
      canvasHeight: process.env.CANVAS_HEIGHT || 2500,
      backgroundColor: process.env.BACKGROUND_COLOR || '#f3f3f4',
      shadowOpacity: process.env.SHADOW_OPACITY || 0.18,
    };

    this.shopify = new ShopifyClient({
      storeUrl: this.config.storeUrl,
      accessToken: this.config.accessToken,
    });

    this.imageProcessor = new ImageProcessor(this.config);
    this.scaler = new ProductScaler(
      parseInt(this.config.canvasWidth),
      parseInt(this.config.canvasHeight)
    );

    this.outputDir = './output';
    this.categories = ['tall_thin', 'wide', 'small_accessory', 'default'];
  }

  /**
   * Main test execution
   * @param {number} perCategory - Number of examples per category (default: 3)
   */
  async run(perCategory = 3) {
    try {
      console.log(`=== Test Run: Finding ${perCategory} Examples Per Category ===\n`);

      // Create output directory
      await fs.mkdir(this.outputDir, { recursive: true });

      // 1. Find examples
      console.log('Finding example products...');
      const examples = await this.findExamples(perCategory);

      if (examples.length === 0) {
        console.log('No example products found!');
        return;
      }

      // 2. Process examples
      console.log('\nProcessing example products...');
      const results = await this.processExamples(examples);

      // 3. Generate comparison HTML
      console.log('\nGenerating comparison HTML...');
      await this.generateComparisonHTML(results);

      console.log('\n✓ Test run complete!');
      console.log(`Open comparison.html in your browser to review results.`);
      console.log(`Total products tested: ${results.length}`);

    } catch (error) {
      console.error('Test run failed:', error);
      throw error;
    }
  }

  /**
   * Find example products - multiple per category for better testing
   * @param {number} perCategory - Number of examples per category (default: 3)
   * @returns {Promise<Array>} Array of example products
   */
  async findExamples(perCategory = 3) {
    const allProducts = await this.shopify.getAllProducts();
    const examples = [];
    const categoryCount = {
      tall_thin: 0,
      wide: 0,
      small_accessory: 0,
      default: 0
    };

    console.log(`Scanning ${allProducts.length} products for ${perCategory} examples per category...`);

    for (const product of allProducts) {
      // Check if we have enough examples for all categories
      const allCategoriesFull = Object.values(categoryCount).every(count => count >= perCategory);
      if (allCategoriesFull) {
        break;
      }

      // Skip products without images
      if (!product.images || product.images.length === 0) {
        continue;
      }

      const image = product.images[0];

      try {
        // Download and check dimensions
        const buffer = await this.shopify.downloadImage(image.src);
        const dimensions = await this.imageProcessor.getImageDimensions(buffer);

        // Categorize
        const { category } = this.scaler.categorizeProduct(
          dimensions.width,
          dimensions.height,
          product.title,
          product.product_type
        );

        // Add if we need more examples of this category
        if (categoryCount[category] < perCategory) {
          categoryCount[category]++;
          examples.push({
            product,
            image,
            dimensions,
            category,
            buffer
          });
          console.log(`✓ Found ${category} (${categoryCount[category]}/${perCategory}): ${product.title}`);
        }

      } catch (error) {
        console.error(`Error checking product ${product.id}:`, error.message);
      }
    }

    console.log(`\nFound ${examples.length} total examples:`);
    Object.entries(categoryCount).forEach(([cat, count]) => {
      console.log(`  ${cat}: ${count}`);
    });
    return examples;
  }

  /**
   * Process example products locally
   * @param {Array} examples - Example products
   * @returns {Promise<Array>} Processing results
   */
  async processExamples(examples) {
    const results = [];

    for (const example of examples) {
      try {
        console.log(`\nProcessing: ${example.product.title}`);

        // Process image
        const result = await this.imageProcessor.processImage(example.buffer, {
          title: example.product.title,
          type: example.product.product_type
        });

        // Save original
        const originalPath = path.join(
          this.outputDir,
          `original_${example.category}_${example.product.id}.jpg`
        );
        await fs.writeFile(originalPath, example.buffer);

        // Save processed
        const processedPath = path.join(
          this.outputDir,
          `processed_${example.category}_${example.product.id}.webp`
        );
        await fs.writeFile(processedPath, result.buffer);

        results.push({
          product: example.product,
          category: example.category,
          originalPath,
          processedPath,
          originalDimensions: example.dimensions,
          scalingInfo: result.scalingInfo,
          originalSize: example.buffer.length,
          processedSize: result.buffer.length
        });

        console.log(`✓ Saved: ${path.basename(processedPath)}`);

      } catch (error) {
        console.error(`Error processing ${example.product.title}:`, error.message);
      }
    }

    return results;
  }

  /**
   * Generate comparison HTML
   * @param {Array} results - Processing results
   */
  async generateComparisonHTML(results) {
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Shopify Image Harmonization - Test Results</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f5f5;
      padding: 40px 20px;
    }
    .container {
      max-width: 1400px;
      margin: 0 auto;
    }
    h1 {
      font-size: 32px;
      margin-bottom: 10px;
      color: #333;
    }
    .subtitle {
      color: #666;
      margin-bottom: 30px;
    }
    .checklist {
      background: white;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 30px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .checklist h2 {
      margin-bottom: 15px;
      color: #333;
    }
    .checklist label {
      display: block;
      padding: 8px 0;
      cursor: pointer;
    }
    .checklist input[type="checkbox"] {
      margin-right: 10px;
      cursor: pointer;
    }
    .comparison-grid {
      display: grid;
      gap: 30px;
    }
    .comparison-card {
      background: white;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .card-header {
      padding: 20px;
      border-bottom: 1px solid #eee;
    }
    .card-title {
      font-size: 20px;
      margin-bottom: 10px;
      color: #333;
    }
    .category-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      margin-bottom: 10px;
    }
    .badge-tall_thin { background: #e3f2fd; color: #1976d2; }
    .badge-wide { background: #f3e5f5; color: #7b1fa2; }
    .badge-small_accessory { background: #fff3e0; color: #f57c00; }
    .badge-default { background: #e8f5e9; color: #388e3c; }
    .card-meta {
      font-size: 14px;
      color: #666;
      line-height: 1.6;
    }
    .images-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      padding: 20px;
      background: #fafafa;
    }
    .image-wrapper {
      text-align: center;
    }
    .image-label {
      font-weight: 600;
      margin-bottom: 10px;
      color: #333;
    }
    .image-box {
      background: white;
      padding: 20px;
      border-radius: 4px;
      border: 1px solid #ddd;
    }
    .image-box img {
      max-width: 100%;
      height: auto;
      display: block;
      margin: 0 auto;
    }
    .image-info {
      margin-top: 10px;
      font-size: 12px;
      color: #666;
      line-height: 1.5;
    }
    .stats {
      padding: 20px;
      background: #f9f9f9;
      border-top: 1px solid #eee;
    }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
    }
    .stat-item {
      font-size: 14px;
      color: #666;
    }
    .stat-label {
      font-weight: 600;
      color: #333;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Shopify Image Harmonization</h1>
    <p class="subtitle">Test Results - Category Examples Comparison</p>

    <div class="checklist">
      <h2>Quality Verification Checklist</h2>
      <label><input type="checkbox"> Shadow grounded to base of product</label>
      <label><input type="checkbox"> Correct category-based scaling applied</label>
      <label><input type="checkbox"> Background removal clean through 'holes' (dripper test)</label>
      <label><input type="checkbox"> Background color #f3f3f4 matches site whitespace</label>
      <label><input type="checkbox"> Shadow opacity at 18%</label>
      <label><input type="checkbox"> Product properly centered on canvas</label>
      <label><input type="checkbox"> WebP format with good quality</label>
    </div>

    ${this.generateCategoryGroups(results)}
  </div>
</body>
</html>`;

    await fs.writeFile('./comparison.html', html);
    console.log('✓ Generated comparison.html');
  }

  /**
   * Generate category groups for better organization
   * @param {Array} results - All processing results
   * @returns {string} HTML string
   */
  generateCategoryGroups(results) {
    // Group results by category
    const grouped = {
      tall_thin: [],
      wide: [],
      small_accessory: [],
      default: []
    };

    results.forEach(result => {
      if (grouped[result.category]) {
        grouped[result.category].push(result);
      }
    });

    // Generate HTML for each category
    const categoryNames = {
      tall_thin: 'Tall/Thin Products',
      wide: 'Wide Products',
      small_accessory: 'Small/Accessory Products',
      default: 'Default Products'
    };

    let html = '';
    Object.entries(grouped).forEach(([category, items]) => {
      if (items.length > 0) {
        html += `
    <div style="margin-top: 40px;">
      <h2 style="font-size: 24px; margin-bottom: 20px; color: #333; padding: 0 20px;">
        ${categoryNames[category]} (${items.length})
      </h2>
      <div class="comparison-grid">
        ${items.map(result => this.generateComparisonCard(result)).join('\n')}
      </div>
    </div>`;
      }
    });

    return html;
  }

  /**
   * Generate HTML for a comparison card
   * @param {Object} result - Processing result
   * @returns {string} HTML string
   */
  generateComparisonCard(result) {
    const formatBytes = (bytes) => {
      return (bytes / 1024).toFixed(2) + ' KB';
    };

    return `
      <div class="comparison-card">
        <div class="card-header">
          <div class="category-badge badge-${result.category}">${result.category.replace('_', ' ')}</div>
          <h3 class="card-title">${result.product.title}</h3>
          <div class="card-meta">
            <div><strong>Product ID:</strong> ${result.product.id}</div>
            <div><strong>Type:</strong> ${result.product.product_type || 'N/A'}</div>
            <div><strong>Scaling Reason:</strong> ${result.scalingInfo.reason}</div>
          </div>
        </div>

        <div class="images-container">
          <div class="image-wrapper">
            <div class="image-label">Original</div>
            <div class="image-box">
              <img src="${result.originalPath}" alt="Original">
            </div>
            <div class="image-info">
              <div>${result.originalDimensions.width} × ${result.originalDimensions.height} px</div>
              <div>Size: ${formatBytes(result.originalSize)}</div>
            </div>
          </div>

          <div class="image-wrapper">
            <div class="image-label">Processed</div>
            <div class="image-box" style="background: #f3f3f4;">
              <img src="${result.processedPath}" alt="Processed">
            </div>
            <div class="image-info">
              <div>${result.scalingInfo.canvas.width} × ${result.scalingInfo.canvas.height} px</div>
              <div>Product: ${result.scalingInfo.scaled.width} × ${result.scalingInfo.scaled.height} px</div>
              <div>Size: ${formatBytes(result.processedSize)}</div>
              <div>WebP Format</div>
            </div>
          </div>
        </div>

        <div class="stats">
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-label">Aspect Ratio</div>
              <div>${result.scalingInfo.aspectRatio}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Scale Factor</div>
              <div>${(result.scalingInfo.scaled.scaleFactor * 100).toFixed(1)}%</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Size Reduction</div>
              <div>${(((result.originalSize - result.processedSize) / result.originalSize) * 100).toFixed(1)}%</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">Category</div>
              <div>${result.category.replace('_', ' ').toUpperCase()}</div>
            </div>
          </div>
        </div>
      </div>`;
  }
}

// Parse command line arguments
const args = process.argv.slice(2);
let perCategory = 3; // default

// Check for --count or -c flag
const countIndex = args.findIndex(arg => arg === '--count' || arg === '-c');
if (countIndex !== -1 && args[countIndex + 1]) {
  perCategory = parseInt(args[countIndex + 1]);
  if (isNaN(perCategory) || perCategory < 1) {
    console.error('Error: --count must be a positive number');
    process.exit(1);
  }
}

// Show usage help
if (args.includes('--help') || args.includes('-h')) {
  console.log(`
Test Runner - Process multiple examples per category

Usage:
  npm test                    # Process 3 examples per category (default)
  npm test -- --count 5       # Process 5 examples per category
  npm test -- -c 10           # Process 10 examples per category

This will:
  - Find N products from each category (tall_thin, wide, small_accessory, default)
  - Process them locally (no upload to Shopify)
  - Generate comparison.html for visual review
  - Save all examples to output/ directory
  `);
  process.exit(0);
}

// Run test
console.log(`Using ${perCategory} examples per category\n`);
const runner = new TestRunner();
runner.run(perCategory).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
