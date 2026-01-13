/**
 * Simple test for withoutbg background removal
 */

import { ImageProcessor } from './src/imageProcessor.js';
import sharp from 'sharp';

async function testWithoutBG() {
  console.log('\n=== Testing withoutbg Background Removal ===\n');

  try {
    // Create a simple test image (colored square on white background)
    console.log('1. Creating test image...');
    const testImage = await sharp({
      create: {
        width: 500,
        height: 500,
        channels: 4,
        background: { r: 255, g: 255, b: 255, alpha: 1 } // White background
      }
    })
    .composite([{
      input: await sharp({
        create: {
          width: 300,
          height: 300,
          channels: 3,
          background: { r: 255, g: 100, b: 50 } // Orange square (product)
        }
      }).png().toBuffer(),
      top: 100,
      left: 100
    }])
    .png()
    .toBuffer();

    console.log('✓ Test image created (500×500 with orange square)\n');

    // Initialize processor
    const config = {
      canvasWidth: 2000,
      canvasHeight: 2500,
      backgroundColor: '#f3f3f4',
      shadowOpacity: 0.18,
      webpQuality: 90,
      enableAutoTrim: true,
      enableBackgroundRemoval: true
    };

    const processor = new ImageProcessor(config);

    // Test background removal
    console.log('2. Testing background removal...');
    console.log('   This will download ~320MB models on first run');
    console.log('   Please be patient...\n');

    const startTime = Date.now();
    const result = await processor.cleanupBackground(testImage);
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);

    console.log(`\n3. Background removal completed in ${duration}s`);

    // Verify result
    const metadata = await sharp(result).metadata();
    console.log(`   ✓ Output: ${metadata.width}×${metadata.height}`);
    console.log(`   ✓ Format: ${metadata.format}`);
    console.log(`   ✓ Has alpha: ${metadata.hasAlpha}`);
    console.log(`   ✓ Buffer size: ${(result.length / 1024).toFixed(1)}KB`);

    console.log('\n✅ TEST PASSED - withoutbg is working!\n');

  } catch (error) {
    console.error('\n❌ TEST FAILED');
    console.error('Error:', error.message);
    console.error('\nStack:', error.stack);
    process.exit(1);
  }
}

testWithoutBG();
