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
 * Your TestRunner Class stays exactly here...
 */
class TestRunner {
  // ... (keep all your existing class code)
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
