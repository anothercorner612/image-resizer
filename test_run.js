// --- 1. ALL IMPORTS FIRST ---
import * as dotenv from 'dotenv';
import { ShopifyClient } from './src/shopify.js';
import { ImageProcessor } from './src/imageProcessor.js';
import { ProductScaler } from './src/scaler.js';
import fs from 'fs/promises';
import path from 'path';

// --- 2. INITIALIZE DOTENV ---
dotenv.config();

// --- 3. LOG START IMMEDIATELY ---
console.log("🚀 SCRIPT STARTING...");

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
    };

    this.shopify = new ShopifyClient(this.config);
    this.imageProcessor = new ImageProcessor(this.config);
    this.scaler = new ProductScaler(
      parseInt(this.config.canvasWidth),
      parseInt(this.config.canvasHeight)
    );

    this.outputDir = './output';
  }

  async run(perCategory = 3) {
    try {
      console.log(`=== Test Run: Finding ${perCategory} Examples Per Category ===\n`);

      // Create output directory
      await fs.mkdir(this.outputDir, { recursive: true });

      // 1. Find examples
      console.log('Finding example products...');
      const allProducts = await this.shopify.getAllProducts();
      
      // For this test run, we'll just process the first few found
      const examples = allProducts.slice(0, perCategory * 7); 

      if (examples.length === 0) {
        console.log('No products found in Shopify!');
        return;
      }

      // 2. Process examples
      for (const product of examples) {
        if (!product.images || !product.images[0]) continue;
        
        console.log(`Processing: ${product.title}`);
        const buffer = await this.shopify.downloadImage(product.images[0].src);
        const result = await this.imageProcessor.processImage(buffer, { title: product.title });
        
        const outPath = path.join(this.outputDir, `processed_${product.id}.webp`);
        await fs.writeFile(outPath, result.buffer);
        console.log(`✓ Saved to ${outPath}`);
      }

      console.log('\n✓ Test run complete!');
    } catch (error) {
      console.error('Run encountered an error:', error);
      throw error;
    }
  }
}

// --- 4. EXECUTION BLOCK WITH CATCH-ALL ---
console.log("🔧 Initializing Runner...");

try {
  const runner = new TestRunner();
  console.log("📡 Starting Shopify Scan...");
  
  // Parse command line arguments
  const args = process.argv.slice(2);
  let perCategory = 3;
  const countIndex = args.findIndex(arg => arg === '--count' || arg === '-c');
  if (countIndex !== -1 && args[countIndex + 1]) {
    perCategory = parseInt(args[countIndex + 1]);
  }

  runner.run(perCategory).then(() => {
    console.log("✅ Process Finished");
  }).catch(err => {
    console.error("❌ ERROR DURING RUN:", err);
  });

} catch (err) {
  console.error("❌ CRITICAL INITIALIZATION ERROR:", err);
  console.error(err.stack);
}
