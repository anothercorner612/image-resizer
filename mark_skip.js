#!/usr/bin/env node
/**
 * Utility to mark products as "skip" so they won't be processed
 *
 * Usage:
 *   node mark_skip.js <product_id> [reason]
 *   node mark_skip.js 1234567890 "White edges issue"
 *   node mark_skip.js 1234567890
 */

import dotenv from 'dotenv';
import { ShopifyClient } from './src/shopify.js';
import { MetafieldManager } from './src/metafields.js';

// Load environment variables
dotenv.config();

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log('\n❌ Error: Product ID required\n');
    console.log('Usage:');
    console.log('  node mark_skip.js <product_id> [reason]');
    console.log('\nExamples:');
    console.log('  node mark_skip.js 1234567890');
    console.log('  node mark_skip.js 1234567890 "White edges issue"');
    console.log('  node mark_skip.js 1234567890 "Already harmonized manually"\n');
    process.exit(1);
  }

  const productId = args[0];
  const reason = args.slice(1).join(' ') || 'Manually marked to skip';

  try {
    console.log('\n🔧 Marking product as skipped...');
    console.log(`Product ID: ${productId}`);
    console.log(`Reason: ${reason}\n`);

    // Initialize clients
    const shopifyClient = new ShopifyClient({
      shopUrl: process.env.SHOPIFY_STORE_URL,
      accessToken: process.env.SHOPIFY_ACCESS_TOKEN,
    });

    const metafieldManager = new MetafieldManager(shopifyClient);

    // Get product info
    const product = await shopifyClient.getProduct(productId);
    console.log(`Product: ${product.title}\n`);

    // Mark as skipped
    await metafieldManager.markAsSkipped(productId, {
      productTitle: product.title,
      reason: reason,
    });

    console.log('\n✓ Product marked as skipped successfully!');
    console.log('\nThis product will now be skipped during processing.');
    console.log('To process it later, delete the metafield or mark it as pending.\n');

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    console.error('\nMake sure:');
    console.error('- .env file exists with valid Shopify credentials');
    console.error('- Product ID is correct');
    console.error('- You have API access to the product\n');
    process.exit(1);
  }
}

main();
